from decimal import Decimal

from django.urls import reverse

from catalogo.models import Produto
from contas.models import Usuario
from catalogo.servicos import PesquisarPor, buscar_por_codigo, pesquisar_produtos

# Campo obrigatório do formulário, com o valor padrão.
OBRIGATORIOS = {"unidade": "UN"}


def test_pesquisa_por_nome_codigo_e_codigo_de_barras(produto):
    assert list(pesquisar_produtos("caneca", PesquisarPor.NOME)) == [produto]
    assert list(pesquisar_produtos("can-01", PesquisarPor.CODIGO)) == [produto]
    assert list(pesquisar_produtos("7890000000048", PesquisarPor.CODIGO_BARRAS)) == [produto]
    assert not pesquisar_produtos("camiseta", PesquisarPor.NOME).exists()


def test_pesquisa_oculta_inativos_salvo_quando_solicitado(produto):
    produto.ativo = False
    produto.save()
    assert not pesquisar_produtos("caneca").exists()
    assert list(pesquisar_produtos("caneca", incluir_inativos=True)) == [produto]


def test_pesquisa_por_categoria(produto, servico):
    Produto.objects.filter(pk=produto.pk).update(categoria=Produto.Categoria.CAFE)
    assert list(pesquisar_produtos(categoria=Produto.Categoria.CAFE)) == [produto]
    assert list(pesquisar_produtos(categoria=Produto.Categoria.OUTRO)) == [servico]


def test_buscar_por_codigo_interno_ou_de_barras(produto):
    assert buscar_por_codigo("can-01") == produto
    assert buscar_por_codigo("7890000000048") == produto
    assert buscar_por_codigo("nada") is None


def test_lista_de_produtos_tem_dez_por_pagina(client, voluntario, bolsista):
    for indice in range(12):
        Produto.objects.create(
            codigo=f"P{indice:02d}",
            nome=f"Produto {indice:02d}",
            preco_unitario=Decimal("1.00"),
            criado_por=bolsista,
            alterado_por=bolsista,
        )
    client.force_login(voluntario)
    resposta = client.get(reverse("catalogo:lista_produtos"))
    assert len(resposta.context["produtos"]) == 10
    assert resposta.context["page_obj"].paginator.num_pages == 2


def test_voluntario_pesquisa_mas_nao_cadastra(client, voluntario):
    client.force_login(voluntario)
    assert client.get(reverse("catalogo:lista_produtos")).status_code == 200
    assert client.get(reverse("catalogo:cadastrar_produto")).status_code == 403


def test_bolsista_cadastra_produto_com_rastreabilidade(client, bolsista):
    client.force_login(bolsista)
    resposta = client.post(
        reverse("catalogo:cadastrar_produto"),
        {
            "codigo": "bri-01",
            "nome": "Brigadeiro",
            "categoria": "doce",
            "preco_unitario": "2.50",
            "codigo_barras": "",
            "controla_estoque": "on",
            **OBRIGATORIOS,
        },
    )
    produto = Produto.objects.get(codigo="BRI-01")
    assert resposta.status_code == 302
    assert produto.codigo_barras is None
    assert produto.criado_por == bolsista
    assert produto.saldo_estoque == 0


def test_inativacao_preserva_o_produto(client, bolsista, produto):
    client.force_login(bolsista)
    client.post(reverse("catalogo:alternar_situacao", args=[produto.pk]))
    produto.refresh_from_db()
    assert produto.ativo is False


def test_nao_deixa_de_controlar_estoque_com_saldo(client, bolsista, produto):
    Produto.objects.filter(pk=produto.pk).update(saldo_estoque=3)
    client.force_login(bolsista)
    resposta = client.post(
        reverse("catalogo:editar_produto", args=[produto.pk]),
        {"codigo": produto.codigo, "nome": produto.nome, "preco_unitario": "30.00", **OBRIGATORIOS},
    )
    assert resposta.status_code == 200
    assert "controla_estoque" in resposta.context["form"].errors


def test_edicao_do_cadastro_nao_altera_o_saldo(client, bolsista, produto):
    Produto.objects.filter(pk=produto.pk).update(saldo_estoque=8)
    client.force_login(bolsista)
    client.post(
        reverse("catalogo:editar_produto", args=[produto.pk]),
        {
            "codigo": produto.codigo,
            "nome": "Caneca nova",
            "categoria": "outro",
            "preco_unitario": "32.00",
            "controla_estoque": "on",
            **OBRIGATORIOS,
        },
    )
    produto.refresh_from_db()
    assert (produto.nome, produto.saldo_estoque) == ("Caneca nova", 8)


# Venda e lucro ------------------------------------------------------


def _cadastrar(client, **campos):
    dados = {"codigo": "CAF-P", "nome": "Café", "categoria": "cafe", "preco_unitario": "4.00", **OBRIGATORIOS}
    return client.post(reverse("catalogo:cadastrar_produto"), {**dados, **campos})


def test_cadastro_com_unidade_custo_e_codigo_de_barras(client, bolsista):
    client.force_login(bolsista)
    resposta = _cadastrar(client, unidade="COPO", preco_custo="1.00", codigo_barras=" 123 ")
    assert resposta.status_code == 302
    produto = Produto.objects.get(codigo="CAF-P")
    assert (produto.unidade, produto.codigo_barras) == ("COPO", "123")
    assert produto.lucro_unitario == Decimal("3.00")
    assert produto.margem_percentual == Decimal("75")


def test_lucro_e_margem_sem_preco_de_custo(produto):
    assert produto.lucro_unitario is None
    assert produto.margem_percentual is None


def test_custo_e_margem_aparecem_so_para_gestores(client, voluntario, bolsista, produto):
    Produto.objects.filter(pk=produto.pk).update(preco_custo=Decimal("12.00"))
    url = reverse("catalogo:detalhe_produto", args=[produto.pk])
    client.force_login(voluntario)
    assert "Preço de custo" not in client.get(url).content.decode()
    client.force_login(bolsista)
    assert "Preço de custo" in client.get(url).content.decode()


def test_admin_cadastra_produto_com_autoria(client, db):
    raiz = Usuario.objects.create_superuser("raiz", password="senha-original-123")
    client.force_login(raiz)
    dados = {"codigo": "adm-1", "nome": "Adesivo", "categoria": Produto.Categoria.choices[0][0],
             "preco_unitario": "3.00", "controla_estoque": "on", "ativo": "on", **OBRIGATORIOS}
    resposta = client.post(reverse("admin:catalogo_produto_add"), dados)
    assert resposta.status_code == 302
    produto = Produto.objects.get(codigo="ADM-1")
    assert produto.criado_por == raiz and produto.alterado_por == raiz


def test_admin_aplica_as_validacoes_do_cadastro(client, produto, bolsista):
    from estoque.models import Movimentacao
    from estoque.servicos import registrar_movimentacao

    registrar_movimentacao(tipo=Movimentacao.Tipo.ENTRADA, produto=produto, quantidade=2, usuario=bolsista)
    client.force_login(Usuario.objects.create_superuser("raiz", password="senha-original-123"))
    dados = {"codigo": produto.codigo, "nome": produto.nome, "categoria": produto.categoria,
             "preco_unitario": "30.00", "ativo": "on", **OBRIGATORIOS}  # sem controla_estoque
    resposta = client.post(reverse("admin:catalogo_produto_change", args=[produto.pk]), dados)
    assert resposta.status_code == 200
    produto.refresh_from_db()
    assert produto.controla_estoque


# Código de barras no início e API externa ----------------------------


def test_codigo_de_barras_eh_o_primeiro_campo_do_formulario():
    from catalogo.forms import FormularioProduto

    formulario = FormularioProduto()
    grupos = formulario.grupos()
    assert grupos[0][1][0].name == "codigo_barras"
    assert list(formulario.fields)[0] == "codigo_barras"


def test_consultar_codigo_barras_externo_preenche_campos(monkeypatch):
    import io
    import json
    from catalogo.servicos import consultar_codigo_barras_externo

    payload = {
        "status": 1,
        "product": {
            "product_name_pt": "Refrigerante Guaraná",
            "generic_name_pt": "Refrigerante de guaraná",
            "quantity": "350 ml",
            "brands": "Antarctica, Ambev",
            "categories_tags": ["en:beverages", "en:sodas"],
        },
    }

    class _RespostaFake(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=5: _RespostaFake(json.dumps(payload).encode("utf-8")),
    )

    dados = consultar_codigo_barras_externo("7891991010856")
    assert dados == {
        "nome": "Refrigerante Guaraná 350 ml",
        "marca": "Antarctica, Ambev",
        "categoria": Produto.Categoria.BEBIDA,
        "descricao": "Refrigerante de guaraná",
        "fonte": "Open Food Facts",
    }


def test_consultar_codigo_barras_externo_erro_rede(monkeypatch):
    import urllib.error
    import pytest
    from catalogo.servicos import ErroConsultaCodigoBarras, consultar_codigo_barras_externo

    def _falhar(*args, **kwargs):
        raise urllib.error.URLError("sem rede")

    monkeypatch.setattr("urllib.request.urlopen", _falhar)
    with pytest.raises(ErroConsultaCodigoBarras):
        consultar_codigo_barras_externo("7891991010856")


def test_view_consultar_codigo_barras_permissoes_e_respostas(client, voluntario, bolsista, monkeypatch):
    url = reverse("catalogo:consultar_codigo_barras")

    client.force_login(voluntario)
    assert client.get(url, {"codigo": "7891991010856"}).status_code == 403

    client.force_login(bolsista)
    assert client.get(url).status_code == 400

    monkeypatch.setattr(
        "catalogo.views.consultar_codigo_barras_externo",
        lambda codigo: {
            "nome": "Biscoito Recheado 130 g",
            "marca": "Oreo",
            "categoria": Produto.Categoria.DOCE,
            "descricao": "Biscoito de chocolate",
            "fonte": "Open Food Facts",
        },
    )
    resposta = client.get(url, {"codigo": "7622210602084"})
    assert resposta.status_code == 200
    assert resposta.json() == {
        "encontrado": True,
        "dados": {
            "nome": "Biscoito Recheado 130 g",
            "marca": "Oreo",
            "categoria": Produto.Categoria.DOCE,
            "descricao": "Biscoito de chocolate",
            "fonte": "Open Food Facts",
        },
    }

    monkeypatch.setattr("catalogo.views.consultar_codigo_barras_externo", lambda codigo: None)
    resposta_nao_encontrado = client.get(url, {"codigo": "00000000"})
    assert resposta_nao_encontrado.status_code == 200
    assert resposta_nao_encontrado.json() == {"encontrado": False}
