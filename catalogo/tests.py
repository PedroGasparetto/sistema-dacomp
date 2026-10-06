from decimal import Decimal

from django.urls import reverse

from catalogo.models import Produto
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
