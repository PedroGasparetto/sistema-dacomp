"""Consultas e regras de produtos reutilizadas pelo catálogo e pelas vendas."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import TextChoices

from .models import Produto


class PesquisarPor(TextChoices):
    NOME = "nome", "Nome"
    CODIGO = "codigo", "Código interno"
    CODIGO_BARRAS = "barras", "Código de barras"


def pesquisar_produtos(termo="", por=PesquisarPor.NOME, incluir_inativos=False, categoria=""):
    produtos = Produto.objects.all()
    if not incluir_inativos:
        produtos = produtos.filter(ativo=True)
    if categoria:
        produtos = produtos.filter(categoria=categoria)

    termo = termo.strip()
    if not termo:
        return produtos
    if por == PesquisarPor.CODIGO:
        return produtos.filter(codigo__iexact=termo)
    if por == PesquisarPor.CODIGO_BARRAS:
        return produtos.filter(codigo_barras=termo)
    return produtos.filter(nome__icontains=termo)


def buscar_por_codigo(valor):
    """Identifica um item pelo código interno ou pelo código lido no leitor."""
    valor = valor.strip()
    if not valor:
        return None
    return (
        Produto.objects.filter(codigo__iexact=valor).first()
        or Produto.objects.filter(codigo_barras=valor).first()
    )


@transaction.atomic
def baixar_saldo(*, produto, quantidade):
    """Baixa do estoque ao concluir uma venda (passo do caso de uso Registrar Venda).

    Deve ser chamada dentro da transação da venda: se faltar saldo para
    qualquer item, a venda inteira é desfeita.
    """
    produto_bloqueado = Produto.objects.select_for_update().get(pk=produto.pk)
    if not produto_bloqueado.controla_estoque:
        return produto_bloqueado
    if quantidade > produto_bloqueado.saldo_estoque:
        raise ValidationError(
            f"Saldo insuficiente de {produto_bloqueado.nome}: "
            f"disponível {produto_bloqueado.saldo_estoque}, na venda {quantidade}."
        )
    produto_bloqueado.saldo_estoque -= quantidade
    produto_bloqueado.save(update_fields=["saldo_estoque"])
    return produto_bloqueado
