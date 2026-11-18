"""Regras de negócio do estoque (UC10, UC11, UC12 e UC09).

Este módulo é o único ponto que altera `Produto.saldo_estoque`. As vendas
registram aqui a baixa de cada item e as devoluções, a recomposição do saldo.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum

from catalogo.models import Produto

from .models import Movimentacao

Tipo = Movimentacao.Tipo


def calcular_novo_saldo(tipo, saldo_atual, quantidade):
    """A entrada soma a quantidade recebida; o ajuste substitui pelo saldo contado."""
    if tipo == Tipo.ENTRADA:
        return saldo_atual + quantidade
    if tipo == Tipo.AJUSTE:
        return quantidade
    raise ValueError(f"Tipo de movimentação não suportado: {tipo}")


def validar_movimentacao(*, tipo, produto, quantidade, motivo=""):
    """Valida uma entrada ou um ajuste (UC10, sequências alternativas A1 e A2)."""
    erros = {}

    if not produto.controla_estoque:
        erros["produto"] = "Este item não possui controle de estoque."
    elif tipo == Tipo.ENTRADA and not produto.ativo:
        erros["produto"] = "Produto inativo não pode receber entrada de reposição."

    if tipo == Tipo.ENTRADA and quantidade <= 0:
        erros["quantidade"] = "A quantidade recebida deve ser maior que zero."
    elif tipo == Tipo.AJUSTE:
        if quantidade < 0:
            erros["quantidade"] = "O saldo encontrado não pode ser negativo."
        elif quantidade == produto.saldo_estoque:
            erros["quantidade"] = "O saldo encontrado é igual ao saldo atual; não há ajuste a registrar."
        if not motivo:
            erros["motivo"] = "Informe o motivo do ajuste."

    if erros:
        raise ValidationError(erros)


@transaction.atomic
def registrar_movimentacao(*, tipo, produto, quantidade, usuario, motivo="", observacao=""):
    """UC10 – registra a movimentação e atualiza o saldo em uma única operação."""
    if tipo not in (Tipo.ENTRADA, Tipo.AJUSTE):
        raise ValueError("Use esta função apenas para entradas e ajustes.")

    produto_bloqueado = Produto.objects.select_for_update().get(pk=produto.pk)
    validar_movimentacao(tipo=tipo, produto=produto_bloqueado, quantidade=quantidade, motivo=motivo)

    novo_saldo = calcular_novo_saldo(tipo, produto_bloqueado.saldo_estoque, quantidade)
    return _gravar_movimentacao(
        produto_bloqueado,
        tipo=tipo,
        novo_saldo=novo_saldo,
        usuario=usuario,
        motivo=motivo if tipo == Tipo.AJUSTE else "",
        observacao=observacao,
    )


@transaction.atomic
def registrar_baixa_por_venda(*, produto, quantidade, usuario, referencia):
    """Baixa automática ao concluir uma venda (passo do UC05, não um caso de uso próprio).

    Deve ser chamada dentro da transação da venda: se faltar saldo para
    qualquer item, a venda inteira é desfeita.
    """
    produto_bloqueado = Produto.objects.select_for_update().get(pk=produto.pk)
    if not produto_bloqueado.controla_estoque:
        return None
    if quantidade > produto_bloqueado.saldo_estoque:
        raise ValidationError(
            f"Saldo insuficiente de {produto_bloqueado.nome}: "
            f"disponível {produto_bloqueado.saldo_estoque}, na venda {quantidade}."
        )
    return _gravar_movimentacao(
        produto_bloqueado,
        tipo=Tipo.VENDA,
        novo_saldo=produto_bloqueado.saldo_estoque - quantidade,
        usuario=usuario,
        observacao=referencia,
    )


@transaction.atomic
def registrar_recomposicao_por_devolucao(*, produto, quantidade, usuario, referencia):
    """Devolve ao saldo os itens de uma devolução (passo do UC16).

    Deve ser chamada dentro da transação da devolução. Itens sem controle de
    estoque não geram movimentação.
    """
    if quantidade <= 0:
        raise ValueError("A quantidade devolvida deve ser maior que zero.")
    produto_bloqueado = Produto.objects.select_for_update().get(pk=produto.pk)
    if not produto_bloqueado.controla_estoque:
        return None
    return _gravar_movimentacao(
        produto_bloqueado,
        tipo=Tipo.DEVOLUCAO,
        novo_saldo=produto_bloqueado.saldo_estoque + quantidade,
        usuario=usuario,
        observacao=referencia,
    )


def _gravar_movimentacao(produto_bloqueado, *, tipo, novo_saldo, usuario, motivo="", observacao=""):
    saldo_anterior = produto_bloqueado.saldo_estoque
    movimentacao = Movimentacao.objects.create(
        produto=produto_bloqueado,
        tipo=tipo,
        quantidade_anterior=saldo_anterior,
        variacao=novo_saldo - saldo_anterior,
        quantidade_resultante=novo_saldo,
        motivo=motivo,
        observacao=observacao,
        responsavel=usuario,
    )
    produto_bloqueado.saldo_estoque = novo_saldo
    produto_bloqueado.save(update_fields=["saldo_estoque"])
    return movimentacao


def filtrar_movimentacoes(*, termo_produto="", tipo="", inicio=None, fim=None):
    """UC09 – filtros por produto, tipo e período."""
    movimentacoes = Movimentacao.objects.select_related("produto", "responsavel")

    termo_produto = termo_produto.strip()
    if termo_produto:
        movimentacoes = movimentacoes.filter(
            Q(produto__nome__icontains=termo_produto)
            | Q(produto__codigo__iexact=termo_produto)
            | Q(produto__codigo_barras=termo_produto)
        )
    if tipo:
        movimentacoes = movimentacoes.filter(tipo=tipo)
    if inicio:
        movimentacoes = movimentacoes.filter(realizada_em__date__gte=inicio)
    if fim:
        movimentacoes = movimentacoes.filter(realizada_em__date__lte=fim)
    return movimentacoes


def gerar_relatorio_movimentacoes(**filtros):
    """UC14 – relatório das movimentações filtradas na consulta (UC09).

    Lista os registros do período e soma, por produto, as entradas, os ajustes,
    as baixas por venda e as recomposições por devolução. Nenhum registro é alterado.
    """
    movimentacoes = filtrar_movimentacoes(**filtros).order_by("realizada_em", "id")
    somas = {tipo.value: Sum("variacao", filter=Q(tipo=tipo.value)) for tipo in Tipo}
    por_produto = []
    for linha in (
        movimentacoes.order_by()
        .values("produto__codigo", "produto__nome", "produto__saldo_estoque")
        .annotate(**somas)
        .order_by("produto__nome")
    ):
        totais = {tipo.value: linha[tipo.value] or 0 for tipo in Tipo}
        por_produto.append(
            {
                "codigo": linha["produto__codigo"],
                "nome": linha["produto__nome"],
                "saldo_atual": linha["produto__saldo_estoque"],
                **totais,
                "variacao_total": sum(totais.values()),
            }
        )
    return {
        "movimentacoes": list(movimentacoes),
        "por_produto": por_produto,
        "totais": {tipo.value: sum(linha[tipo.value] for linha in por_produto) for tipo in Tipo},
    }
