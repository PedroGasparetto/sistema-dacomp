from decimal import Decimal

from django.urls import reverse

from catalogo.models import Produto
from catalogo.servicos import PesquisarPor, buscar_por_codigo, pesquisar_produtos
from catalogo.validadores import gtin_valido

# Campos fiscais obrigatórios no formulário, com os valores padrão.
FISCAIS = {"cfop": "5102", "unidade_comercial": "UN", "origem": "0", "csosn": "102"}


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
            **FISCAIS,
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
        {"codigo": produto.codigo, "nome": produto.nome, "preco_unitario": "30.00", **FISCAIS},
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
            **FISCAIS,
        },
    )
    produto.refresh_from_db()
    assert (produto.nome, produto.saldo_estoque) == ("Caneca nova", 8)


# Dados fiscais e de reposição --------------------------------------------------


def test_gtin_confere_digito_verificador():
    assert gtin_valido("7890000000048")
    assert gtin_valido("2000000000015")
    assert not gtin_valido("7890000000049")
    assert not gtin_valido("12345")


def _cadastrar(client, **campos):
    dados = {"codigo": "REF", "nome": "Refrigerante", "categoria": "bebida", "preco_unitario": "5.00", **FISCAIS}
    return client.post(reverse("catalogo:cadastrar_produto"), {**dados, **campos})


def test_cadastro_normaliza_codigos_fiscais(client, bolsista):
    client.force_login(bolsista)
    resposta = _cadastrar(client, ncm="2202.10.00", cest="03.007.00", codigo_barras="2000000000015")
    assert resposta.status_code == 302
    produto = Produto.objects.get(codigo="REF")
    assert (produto.ncm, produto.cest, produto.codigo_barras) == ("22021000", "0300700", "2000000000015")


def test_cadastro_rejeita_codigos_fiscais_invalidos(client, bolsista):
    client.force_login(bolsista)
    resposta = _cadastrar(client, ncm="2202100", codigo_barras="2000000000016", cfop="1102")
    erros = resposta.context["form"].errors
    assert {"ncm", "codigo_barras", "cfop"} <= set(erros)
    assert not Produto.objects.exists()


def test_margem_e_estoque_minimo(produto):
    produto.preco_custo = Decimal("12.00")
    produto.estoque_minimo = 5
    produto.saldo_estoque = 3
    assert produto.margem_percentual == Decimal("60")
    assert produto.abaixo_do_minimo
    assert produto.gtin_nota == "7890000000048"


def test_filtro_de_itens_para_repor(produto, servico):
    Produto.objects.filter(pk=produto.pk).update(saldo_estoque=10, estoque_minimo=5)
    assert not pesquisar_produtos(para_repor=True).exists()
    Produto.objects.filter(pk=produto.pk).update(saldo_estoque=4)
    assert list(pesquisar_produtos(para_repor=True)) == [produto]  # serviço não entra


def test_custo_e_margem_aparecem_so_para_gestores(client, voluntario, bolsista, produto):
    Produto.objects.filter(pk=produto.pk).update(preco_custo=Decimal("12.00"))
    url = reverse("catalogo:detalhe_produto", args=[produto.pk])
    client.force_login(voluntario)
    assert "Preço de custo" not in client.get(url).content.decode()
    client.force_login(bolsista)
    assert "Preço de custo" in client.get(url).content.decode()
