"""Consultas de produtos reutilizadas pelo catálogo, pelo estoque e pelas vendas."""

from django.db.models import F, Q, TextChoices

from .models import Produto


class PesquisarPor(TextChoices):
    NOME = "nome", "Nome"
    CODIGO = "codigo", "Código interno"
    CODIGO_BARRAS = "barras", "Código de barras"


def filtrar_para_repor(produtos):
    """Itens com controle de estoque zerados ou abaixo do estoque mínimo."""
    return produtos.filter(controla_estoque=True).filter(
        Q(saldo_estoque=0) | Q(saldo_estoque__lt=F("estoque_minimo"))
    )


def pesquisar_produtos(termo="", por=PesquisarPor.NOME, incluir_inativos=False, categoria="", para_repor=False):
    produtos = Produto.objects.all()
    if not incluir_inativos:
        produtos = produtos.filter(ativo=True)
    if categoria:
        produtos = produtos.filter(categoria=categoria)
    if para_repor:
        produtos = filtrar_para_repor(produtos)

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
