"""Regras de negócio do caixa, das vendas e das devoluções (UC01, UC02, UC03, UC12, UC16, UC49 e UC50)."""

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from catalogo.servicos import PesquisarPor, buscar_por_codigo, pesquisar_produtos
from estoque.servicos import registrar_baixa_por_venda, registrar_recomposicao_por_devolucao

from .models import ZERO, Caixa, Devolucao, ItemDevolucao, ItemVenda, Venda

Situacao = Venda.Situacao
FormaPagamento = Venda.FormaPagamento


# Caixa ---------------------------------------------------------------------


def obter_caixa_aberto():
    return Caixa.objects.filter(situacao=Caixa.Situacao.ABERTO).first()


@transaction.atomic
def abrir_caixa(*, usuario, valor_inicial):
    """UC01 – Abrir Caixa."""
    if valor_inicial < ZERO:
        raise ValidationError({"valor_inicial": "O valor inicial deve ser maior ou igual a zero."})
    if obter_caixa_aberto():
        raise ValidationError("Já existe um caixa aberto.")
    return Caixa.objects.create(valor_inicial=valor_inicial, aberto_por=usuario)


def resumir_caixa(caixa):
    """Totais das vendas concluídas no caixa, usados na conferência do fechamento."""
    concluidas = caixa.vendas.filter(situacao=Situacao.CONCLUIDA)
    totais = {
        linha["forma_pagamento"]: linha
        for linha in concluidas.values("forma_pagamento").annotate(valor=Sum("total"), quantidade=Count("id"))
    }
    por_forma = [
        {
            "forma": forma.label,
            "quantidade": totais.get(forma.value, {}).get("quantidade", 0),
            "valor": totais.get(forma.value, {}).get("valor") or ZERO,
        }
        for forma in FormaPagamento
    ]
    recebido_em_dinheiro = totais.get(FormaPagamento.DINHEIRO, {}).get("valor") or ZERO
    total_vendido = sum((linha["valor"] for linha in por_forma), ZERO)

    # Estornos das devoluções feitas neste caixa (UC16); em dinheiro, saem da gaveta.
    estornos = {
        linha["forma_estorno"]: linha["valor"] or ZERO
        for linha in caixa.devolucoes.values("forma_estorno").annotate(valor=Sum("valor_estornado"))
    }
    total_estornado = sum(estornos.values(), ZERO)
    return {
        "por_forma": por_forma,
        "quantidade_vendas": sum(linha["quantidade"] for linha in por_forma),
        "total_vendido": total_vendido,
        "quantidade_devolucoes": caixa.devolucoes.count(),
        "total_estornado": total_estornado,
        "total_liquido": total_vendido - total_estornado,
        "valor_esperado": caixa.valor_inicial + recebido_em_dinheiro - estornos.get(FormaPagamento.DINHEIRO, ZERO),
        "vendas_em_andamento": caixa.vendas.filter(situacao=Situacao.EM_ANDAMENTO).count(),
    }


@transaction.atomic
def fechar_caixa(*, caixa, usuario, valor_contado, justificativa=""):
    """UC02 – Fechar Caixa."""
    caixa = Caixa.objects.select_for_update().get(pk=caixa.pk)
    if caixa.situacao != Caixa.Situacao.ABERTO:
        raise ValidationError("Este caixa já está fechado.")
    if caixa.vendas.filter(situacao=Situacao.EM_ANDAMENTO).exists():
        raise ValidationError(
            "Há venda em andamento neste caixa. Conclua ou cancele a venda antes de fechar."
        )
    if valor_contado < ZERO:
        raise ValidationError({"valor_contado": "O valor contado não pode ser negativo."})

    valor_esperado = resumir_caixa(caixa)["valor_esperado"]
    justificativa = justificativa.strip()
    if valor_contado != valor_esperado and not justificativa:
        raise ValidationError(
            {"justificativa": "Justifique a diferença entre o valor contado e o esperado."}
        )

    caixa.situacao = Caixa.Situacao.FECHADO
    caixa.fechado_por = usuario
    caixa.fechado_em = timezone.now()
    caixa.valor_esperado = valor_esperado
    caixa.valor_contado = valor_contado
    caixa.justificativa = justificativa
    caixa.save()
    return caixa


# Venda ---------------------------------------------------------------------


def obter_venda_em_andamento(usuario, caixa):
    if caixa is None:
        return None
    return (
        Venda.objects.filter(caixa=caixa, operador=usuario, situacao=Situacao.EM_ANDAMENTO)
        .prefetch_related("itens__produto")
        .first()
    )


def iniciar_ou_retomar_venda(usuario):
    """Passos 1–2 do UC03: exige caixa aberto (sequência alternativa A1)."""
    caixa = obter_caixa_aberto()
    if caixa is None:
        raise ValidationError("O caixa está fechado. Abra o caixa para iniciar uma venda.")
    venda = obter_venda_em_andamento(usuario, caixa)
    return venda or Venda.objects.create(caixa=caixa, operador=usuario)


def localizar_produtos_para_venda(termo):
    """Aceita código interno, código de barras (leitor) ou parte do nome."""
    produto = buscar_por_codigo(termo)
    if produto is not None:
        return [produto]
    return list(pesquisar_produtos(termo, PesquisarPor.NOME)[:10]) if termo.strip() else []


def _exigir_em_andamento(venda):
    if venda.situacao != Situacao.EM_ANDAMENTO:
        raise ValidationError("Esta venda não está mais em andamento.")


def _validar_quantidade(produto, quantidade):
    if quantidade <= 0:
        raise ValidationError("A quantidade deve ser maior que zero.")
    if produto.controla_estoque and quantidade > produto.saldo_estoque:
        raise ValidationError(
            f"Saldo insuficiente de {produto.nome}: disponível {produto.saldo_estoque}."
        )


@transaction.atomic
def adicionar_item(*, venda, produto, quantidade=1):
    """Passos 3–6 do UC03; um produto repetido soma à quantidade do item."""
    _exigir_em_andamento(venda)
    if not produto.ativo:
        raise ValidationError(f"{produto.nome} está inativo e não pode ser vendido.")

    item = venda.itens.filter(produto=produto).first()
    nova_quantidade = quantidade + (item.quantidade if item else 0)
    _validar_quantidade(produto, nova_quantidade)

    if item:
        item.quantidade = nova_quantidade
        item.save(update_fields=["quantidade"])
        return item
    return ItemVenda.objects.create(
        venda=venda, produto=produto, quantidade=quantidade, preco_unitario=produto.preco_unitario
    )


def alterar_quantidade(*, item, quantidade):
    _exigir_em_andamento(item.venda)
    _validar_quantidade(item.produto, quantidade)
    item.quantidade = quantidade
    item.save(update_fields=["quantidade"])
    return item


def remover_item(*, item):
    _exigir_em_andamento(item.venda)
    item.delete()


def cancelar_venda(*, venda):
    """Desistência antes da confirmação do recebimento (A5): nada é registrado no estoque."""
    _exigir_em_andamento(venda)
    venda.situacao = Situacao.CANCELADA
    venda.save(update_fields=["situacao"])
    return venda


def verificar_finalizacao(venda):
    """Passo 8 do UC03: venda com itens ativos e saldo suficiente (A3)."""
    _exigir_em_andamento(venda)
    itens = list(venda.itens.select_related("produto"))
    if not itens:
        raise ValidationError("Inclua ao menos um item para finalizar a venda.")
    problemas = []
    for item in itens:
        produto = item.produto
        if not produto.ativo:
            problemas.append(f"{produto.nome} foi inativado.")
        elif produto.controla_estoque and item.quantidade > produto.saldo_estoque:
            problemas.append(f"{produto.nome}: disponível {produto.saldo_estoque}, na venda {item.quantidade}.")
    if problemas:
        raise ValidationError(problemas)


def calcular_troco(total, forma_pagamento, valor_recebido):
    """UC12 – Receber Pagamento: em dinheiro, exige quantia suficiente e calcula o troco."""
    if forma_pagamento != FormaPagamento.DINHEIRO:
        return total, ZERO
    if valor_recebido is None:
        raise ValidationError({"valor_recebido": "Informe a quantia recebida em dinheiro."})
    if valor_recebido < total:
        raise ValidationError({"valor_recebido": "A quantia recebida é menor que o total da venda."})
    return valor_recebido, valor_recebido - total


@transaction.atomic
def concluir_venda(*, venda, forma_pagamento, valor_recebido=None):
    """Passo 10 do UC03 com a inclusão do UC12.

    Venda, pagamento e baixa de estoque são gravados juntos (RNF01): se
    qualquer etapa falhar, nada é registrado.
    """
    venda = Venda.objects.select_for_update().get(pk=venda.pk)
    if venda.caixa.situacao != Caixa.Situacao.ABERTO:
        raise ValidationError("O caixa desta venda foi fechado.")
    verificar_finalizacao(venda)

    total = venda.total_itens
    valor_recebido, troco = calcular_troco(total, forma_pagamento, valor_recebido)

    for item in venda.itens.select_related("produto"):
        registrar_baixa_por_venda(
            produto=item.produto,
            quantidade=item.quantidade,
            usuario=venda.operador,
            referencia=str(venda),
        )

    venda.total = total
    venda.forma_pagamento = forma_pagamento
    venda.valor_recebido = valor_recebido
    venda.troco = troco
    venda.situacao = Situacao.CONCLUIDA
    venda.concluida_em = timezone.now()
    venda.save()
    return venda


# Devolução (UC16) ------------------------------------------------------------


def prazo_devolucao(venda):
    """Último momento em que a venda aceita devolução."""
    return venda.concluida_em + timedelta(days=settings.PRAZO_DEVOLUCAO_DIAS)


def motivo_devolucao_bloqueada(venda, agora=None):
    """Por que a venda não aceita devolução agora, ou None se aceita.

    Sequências alternativas do UC16: venda não concluída, fora do prazo,
    sem itens a devolver ou caixa fechado.
    """
    if venda.situacao != Situacao.CONCLUIDA:
        return "Só vendas concluídas podem ter devolução."
    if (agora or timezone.now()) > prazo_devolucao(venda):
        return f"O prazo de {settings.PRAZO_DEVOLUCAO_DIAS} dias para devolução desta venda terminou."
    if not any(item.quantidade_devolvivel > 0 for item in venda.itens.all()):
        return "Todos os itens desta venda já foram devolvidos."
    if obter_caixa_aberto() is None:
        return "Abra o caixa para registrar a devolução e fazer o estorno."
    return None


@transaction.atomic
def registrar_devolucao(*, venda, quantidades, motivo, usuario):
    """UC16 – Registrar Devolução.

    `quantidades` relaciona o id de cada item da venda à quantidade devolvida.
    O estorno usa a mesma forma de pagamento da venda e o preço praticado nela.
    Devolução, estorno e recomposição do estoque são gravados juntos (RNF01).
    """
    venda = Venda.objects.select_for_update().get(pk=venda.pk)
    bloqueio = motivo_devolucao_bloqueada(venda)
    if bloqueio:
        raise ValidationError(bloqueio)

    motivo = motivo.strip()
    if not motivo:
        raise ValidationError({"motivo": "Informe o motivo da devolução."})

    itens = {item.pk: item for item in venda.itens.select_related("produto")}
    devolvidos = []
    for item_pk, quantidade in quantidades.items():
        item = itens.get(int(item_pk))
        if item is None:
            raise ValidationError("Item não pertence a esta venda.")
        if quantidade < 0:
            raise ValidationError("A quantidade devolvida não pode ser negativa.")
        if quantidade > item.quantidade_devolvivel:
            raise ValidationError(
                f"{item.produto.nome}: é possível devolver no máximo {item.quantidade_devolvivel}."
            )
        if quantidade:
            devolvidos.append((item, quantidade))
    if not devolvidos:
        raise ValidationError("Informe a quantidade de pelo menos um item a devolver.")

    caixa = Caixa.objects.select_for_update().get(pk=obter_caixa_aberto().pk)
    valor = sum((item.preco_unitario * quantidade for item, quantidade in devolvidos), ZERO)
    if venda.forma_pagamento == FormaPagamento.DINHEIRO and valor > resumir_caixa(caixa)["valor_esperado"]:
        raise ValidationError("Não há dinheiro suficiente no caixa para este estorno.")

    devolucao = Devolucao.objects.create(
        venda=venda,
        caixa=caixa,
        operador=usuario,
        motivo=motivo,
        forma_estorno=venda.forma_pagamento,
        valor_estornado=valor,
    )
    for item, quantidade in devolvidos:
        ItemDevolucao.objects.create(devolucao=devolucao, item_venda=item, quantidade=quantidade)
        registrar_recomposicao_por_devolucao(
            produto=item.produto, quantidade=quantidade, usuario=usuario, referencia=f"{devolucao} da {venda}"
        )
    return devolucao


# Consulta ------------------------------------------------------------------


def filtrar_vendas(*, identificador=None, situacao="", operador=None, caixa=None, inicio=None, fim=None):
    """UC49 – Consultar Vendas por identificador, período, operador ou caixa."""
    vendas = Venda.objects.select_related("operador", "caixa")
    if identificador:
        vendas = vendas.filter(pk=identificador)
    if situacao:
        vendas = vendas.filter(situacao=situacao)
    if operador:
        vendas = vendas.filter(operador=operador)
    if caixa:
        vendas = vendas.filter(caixa_id=caixa)
    if inicio:
        vendas = vendas.filter(iniciada_em__date__gte=inicio)
    if fim:
        vendas = vendas.filter(iniciada_em__date__lte=fim)
    return vendas


def gerar_relatorio_vendas(**filtros):
    """UC50 – relatório das vendas filtradas na consulta (UC49).

    Considera apenas vendas concluídas e desconta os estornos das devoluções.
    Nenhum registro é alterado.
    """
    filtros["situacao"] = Situacao.CONCLUIDA
    vendas = filtrar_vendas(**filtros).prefetch_related("devolucoes").order_by("concluida_em", "id")
    totais = {
        linha["forma_pagamento"]: linha
        for linha in vendas.values("forma_pagamento").annotate(valor=Sum("total"), quantidade=Count("id"))
    }
    por_forma = [
        {
            "forma": forma.label,
            "quantidade": totais.get(forma.value, {}).get("quantidade", 0),
            "valor": totais.get(forma.value, {}).get("valor") or ZERO,
        }
        for forma in FormaPagamento
    ]
    total_vendido = sum((linha["valor"] for linha in por_forma), ZERO)
    total_estornado = (
        Devolucao.objects.filter(venda__in=vendas).aggregate(valor=Sum("valor_estornado"))["valor"] or ZERO
    )
    return {
        "vendas": list(vendas),
        "por_forma": por_forma,
        "quantidade_vendas": sum(linha["quantidade"] for linha in por_forma),
        "total_vendido": total_vendido,
        "total_estornado": total_estornado,
        "total_liquido": total_vendido - total_estornado,
    }
