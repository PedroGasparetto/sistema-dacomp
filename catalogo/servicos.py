"""Consultas de produtos reutilizadas pelo catálogo, pelo estoque e pelas vendas."""

import json
import urllib.error
import urllib.parse
import urllib.request

from django.db.models import TextChoices

from .models import Produto

_FONTES_CODIGO_BARRAS = (
    ("Open Food Facts", "https://world.openfoodfacts.org/api/v2/product/{codigo}.json"),
    ("Open Products Facts", "https://world.openproductsfacts.org/api/v2/product/{codigo}.json"),
)
_CAMPOS_API_BARRAS = (
    "product_name,product_name_pt,generic_name,generic_name_pt,"
    "brands,categories,categories_tags,quantity"
)
_USER_AGENT_API = "LojinhaDAcomp/1.0 (https://github.com/dacomp-ufrgs)"

_PALAVRAS_CATEGORIA = (
    (
        Produto.Categoria.CAFE,
        ("coffee", "café", "cafe", "tea", "chá", "cha", "cappuccino", "espresso", "hot-beverage"),
    ),
    (
        Produto.Categoria.BEBIDA,
        (
            "beverage",
            "bebida",
            "soda",
            "refrigerante",
            "water",
            "água",
            "agua",
            "juice",
            "suco",
            "drink",
            "energy-drink",
            "energético",
            "isotonic",
            "isotônico",
            "nectar",
            "néctar",
        ),
    ),
    (
        Produto.Categoria.DOCE,
        (
            "sweet",
            "doce",
            "chocolate",
            "candy",
            "candies",
            "bala",
            "bombom",
            "biscuit",
            "biscoito",
            "bolacha",
            "cookie",
            "cake",
            "bolo",
            "ice-cream",
            "sorvete",
            "confectionery",
            "gummy",
            "wafer",
            "paçoca",
            "pacoca",
        ),
    ),
    (
        Produto.Categoria.LANCHE,
        (
            "salty",
            "salgado",
            "salgadinho",
            "chip",
            "snack",
            "sandwich",
            "sanduíche",
            "bread",
            "pão",
            "cracker",
            "nut",
            "amendoim",
            "popcorn",
            "pipoca",
            "instant-noodle",
            "miojo",
        ),
    ),
)


class ErroConsultaCodigoBarras(Exception):
    """Erro ao consultar a API externa de código de barras."""


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


def _inferir_categoria(produto_api):
    """Mapeia tags/categorias da API externa para `Produto.Categoria`."""
    partes = [
        *(produto_api.get("categories_tags") or []),
        produto_api.get("categories") or "",
    ]
    texto = " ".join(str(p).lower() for p in partes)
    for categoria, palavras in _PALAVRAS_CATEGORIA:
        if any(palavra in texto for palavra in palavras):
            return categoria
    return Produto.Categoria.OUTRO


def _extrair_marca(produto_api):
    brands = (produto_api.get("brands") or "").strip()
    if not brands:
        return ""
    if len(brands) <= 60:
        return brands
    return brands.split(",")[0].strip()[:60]


def _extrair_dados_produto(produto_api, fonte):
    nome = (
        produto_api.get("product_name_pt")
        or produto_api.get("product_name")
        or produto_api.get("generic_name_pt")
        or produto_api.get("generic_name")
        or ""
    ).strip()
    quantidade = (produto_api.get("quantity") or "").strip()
    if nome and quantidade and quantidade.lower() not in nome.lower():
        combinado = f"{nome} {quantidade}"
        if len(combinado) <= 120:
            nome = combinado

    descricao = (
        produto_api.get("generic_name_pt") or produto_api.get("generic_name") or ""
    ).strip()
    if descricao.lower() == nome.lower():
        descricao = ""
    if not descricao and quantidade and quantidade.lower() not in nome.lower():
        descricao = quantidade

    return {
        "nome": nome[:120],
        "marca": _extrair_marca(produto_api),
        "categoria": _inferir_categoria(produto_api),
        "descricao": descricao,
        "fonte": fonte,
    }


def consultar_codigo_barras_externo(codigo_barras, timeout=5):
    """Consulta Open Food Facts / Open Products Facts pelo código de barras.

    Retorna um dicionário com os campos preenchíveis de `Produto` ou `None`
    quando o código não é encontrado. Lança `ErroConsultaCodigoBarras` em caso
    de falha de comunicação com as APIs externas.
    """
    codigo = (codigo_barras or "").strip()
    if not codigo.isdigit() or len(codigo) < 4:
        return None

    codigo_url = urllib.parse.quote(codigo, safe="")
    houve_falha = False
    for fonte, modelo_url in _FONTES_CODIGO_BARRAS:
        url = f"{modelo_url.format(codigo=codigo_url)}?fields={_CAMPOS_API_BARRAS}"
        requisicao = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT_API})
        try:
            with urllib.request.urlopen(requisicao, timeout=timeout) as resposta:
                payload = json.loads(resposta.read().decode("utf-8"))
        except urllib.error.HTTPError as erro:
            if erro.code == 404:
                continue
            houve_falha = True
            continue
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
            houve_falha = True
            continue

        if payload.get("status") == 1 and payload.get("product"):
            dados = _extrair_dados_produto(payload["product"], fonte)
            if any(dados[campo] for campo in ("nome", "marca", "descricao")):
                return dados

    if houve_falha:
        raise ErroConsultaCodigoBarras(
            "Não foi possível consultar a API de código de barras no momento."
        )
    return None
