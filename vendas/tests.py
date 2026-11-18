from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from catalogo.models import Produto
from estoque.models import Movimentacao
from estoque.servicos import registrar_movimentacao
from vendas.models import Caixa, Devolucao, Venda
from vendas.servicos import (
    abrir_caixa,
    adicionar_item,
    cancelar_venda,
    concluir_venda,
    fechar_caixa,
    gerar_relatorio_vendas,
    iniciar_ou_retomar_venda,
    motivo_devolucao_bloqueada,
    registrar_devolucao,
    resumir_caixa,
)

FormaPagamento = Venda.FormaPagamento


@pytest.fixture
def caixa(voluntario):
    return abrir_caixa(usuario=voluntario, valor_inicial=Decimal("50.00"))


@pytest.fixture
def produto_com_saldo(produto, bolsista):
    registrar_movimentacao(tipo=Movimentacao.Tipo.ENTRADA, produto=produto, quantidade=5, usuario=bolsista)
    produto.refresh_from_db()
    return produto


# Caixa ---------------------------------------------------------------------


def test_nao_abre_dois_caixas(caixa, voluntario):
    with pytest.raises(ValidationError):
        abrir_caixa(usuario=voluntario, valor_inicial=Decimal("0"))


def test_venda_exige_caixa_aberto(voluntario):
    with pytest.raises(ValidationError):
        iniciar_ou_retomar_venda(voluntario)


def test_fechamento_bloqueado_com_venda_em_andamento(caixa, voluntario, produto_com_saldo):
    venda = iniciar_ou_retomar_venda(voluntario)
    adicionar_item(venda=venda, produto=produto_com_saldo)
    with pytest.raises(ValidationError):
        fechar_caixa(caixa=caixa, usuario=voluntario, valor_contado=Decimal("50.00"))


def test_fechamento_exige_justificativa_quando_ha_diferenca(caixa, voluntario):
    with pytest.raises(ValidationError) as erro:
        fechar_caixa(caixa=caixa, usuario=voluntario, valor_contado=Decimal("45.00"))
    assert "justificativa" in erro.value.message_dict

    fechado = fechar_caixa(
        caixa=caixa, usuario=voluntario, valor_contado=Decimal("45.00"), justificativa="Troco errado"
    )
    assert fechado.situacao == Caixa.Situacao.FECHADO
    assert fechado.diferenca == Decimal("-5.00")


# Venda ---------------------------------------------------------------------


def test_produto_repetido_soma_quantidade(caixa, voluntario, produto_com_saldo):
    venda = iniciar_ou_retomar_venda(voluntario)
    adicionar_item(venda=venda, produto=produto_com_saldo, quantidade=2)
    adicionar_item(venda=venda, produto=produto_com_saldo, quantidade=1)
    assert venda.itens.get().quantidade == 3


def test_nao_adiciona_alem_do_saldo(caixa, voluntario, produto_com_saldo):
    venda = iniciar_ou_retomar_venda(voluntario)
    with pytest.raises(ValidationError):
        adicionar_item(venda=venda, produto=produto_com_saldo, quantidade=6)


def test_nao_vende_produto_inativo(caixa, voluntario, produto_com_saldo):
    Produto.objects.filter(pk=produto_com_saldo.pk).update(ativo=False)
    produto_com_saldo.refresh_from_db()
    venda = iniciar_ou_retomar_venda(voluntario)
    with pytest.raises(ValidationError):
        adicionar_item(venda=venda, produto=produto_com_saldo)


def test_venda_em_dinheiro_calcula_troco_e_baixa_estoque(caixa, voluntario, produto_com_saldo, servico):
    venda = iniciar_ou_retomar_venda(voluntario)
    adicionar_item(venda=venda, produto=produto_com_saldo, quantidade=2)  # 2 × 30,00
    adicionar_item(venda=venda, produto=servico, quantidade=4)  # 4 × 0,25

    venda = concluir_venda(venda=venda, forma_pagamento=FormaPagamento.DINHEIRO, valor_recebido=Decimal("100.00"))

    assert venda.situacao == Venda.Situacao.CONCLUIDA
    assert venda.total == Decimal("61.00")
    assert venda.troco == Decimal("39.00")
    produto_com_saldo.refresh_from_db()
    assert produto_com_saldo.saldo_estoque == 3
    baixa = Movimentacao.objects.get(tipo=Movimentacao.Tipo.VENDA)
    assert (baixa.variacao, baixa.observacao) == (-2, str(venda))
    assert resumir_caixa(caixa)["valor_esperado"] == Decimal("111.00")


def test_dinheiro_insuficiente_mantem_venda_em_andamento(caixa, voluntario, produto_com_saldo):
    venda = iniciar_ou_retomar_venda(voluntario)
    adicionar_item(venda=venda, produto=produto_com_saldo)
    with pytest.raises(ValidationError):
        concluir_venda(venda=venda, forma_pagamento=FormaPagamento.DINHEIRO, valor_recebido=Decimal("10.00"))
    venda.refresh_from_db()
    produto_com_saldo.refresh_from_db()
    assert venda.situacao == Venda.Situacao.EM_ANDAMENTO
    assert produto_com_saldo.saldo_estoque == 5


def test_saldo_insuficiente_na_conclusao_desfaz_tudo(caixa, voluntario, produto_com_saldo, bolsista):
    venda = iniciar_ou_retomar_venda(voluntario)
    adicionar_item(venda=venda, produto=produto_com_saldo, quantidade=4)
    registrar_movimentacao(
        tipo=Movimentacao.Tipo.AJUSTE,
        produto=produto_com_saldo,
        quantidade=1,
        motivo=Movimentacao.MotivoAjuste.PERDA,
        usuario=bolsista,
    )
    with pytest.raises(ValidationError):
        concluir_venda(venda=venda, forma_pagamento=FormaPagamento.PIX)
    venda.refresh_from_db()
    assert venda.situacao == Venda.Situacao.EM_ANDAMENTO
    assert not Movimentacao.objects.filter(tipo=Movimentacao.Tipo.VENDA).exists()


def test_preco_da_venda_e_preservado(caixa, voluntario, produto_com_saldo):
    venda = iniciar_ou_retomar_venda(voluntario)
    adicionar_item(venda=venda, produto=produto_com_saldo)
    Produto.objects.filter(pk=produto_com_saldo.pk).update(preco_unitario=Decimal("99.00"))
    venda = concluir_venda(venda=venda, forma_pagamento=FormaPagamento.PIX)
    assert venda.total == Decimal("30.00")


def test_cancelamento_nao_altera_estoque(caixa, voluntario, produto_com_saldo):
    venda = iniciar_ou_retomar_venda(voluntario)
    adicionar_item(venda=venda, produto=produto_com_saldo, quantidade=2)
    cancelar_venda(venda=venda)
    produto_com_saldo.refresh_from_db()
    assert produto_com_saldo.saldo_estoque == 5
    assert iniciar_ou_retomar_venda(voluntario).pk != venda.pk


# Telas ---------------------------------------------------------------------


def test_pdv_sem_caixa_oferece_abertura(client, voluntario):
    client.force_login(voluntario)
    resposta = client.get(reverse("vendas:pdv"))
    assert resposta.status_code == 200
    assert reverse("vendas:abrir_caixa") in resposta.content.decode()


def test_grade_de_atalhos_filtra_e_lembra_a_categoria(client, caixa, voluntario, produto, servico):
    Produto.objects.filter(pk=produto.pk).update(categoria=Produto.Categoria.DOCE)
    client.force_login(voluntario)

    resposta = client.get(reverse("vendas:pdv"), {"categoria": Produto.Categoria.DOCE})
    assert [p.codigo for p in resposta.context["atalhos"]] == ["CAN-01"]

    # Depois de adicionar um item, o PDV volta para a mesma categoria.
    client.post(reverse("vendas:adicionar_item"), {"termo": "IMP-PB", "quantidade": "1"})
    assert client.get(reverse("vendas:pdv")).context["categoria_atual"] == Produto.Categoria.DOCE

    resposta = client.get(reverse("vendas:pdv"), {"categoria": "invalida"})
    assert resposta.context["categoria_atual"] == ""


def test_item_preparado_na_hora_e_vendido_sem_estoque(caixa, voluntario, servico):
    venda = iniciar_ou_retomar_venda(voluntario)
    adicionar_item(venda=venda, produto=servico, quantidade=10)
    concluir_venda(venda=venda, forma_pagamento=FormaPagamento.PIX)
    assert not Movimentacao.objects.exists()


def test_fluxo_completo_no_pdv(client, caixa, voluntario, produto_com_saldo):
    client.force_login(voluntario)
    client.post(reverse("vendas:adicionar_item"), {"termo": "7890000000048", "quantidade": "2"})
    venda = Venda.objects.get(situacao=Venda.Situacao.EM_ANDAMENTO)
    assert client.get(reverse("vendas:pdv")).context["total"] == Decimal("60.00")

    resposta = client.post(
        reverse("vendas:pagamento", args=[venda.pk]),
        {"forma_pagamento": FormaPagamento.DINHEIRO, "valor_recebido": "70.00"},
    )
    venda.refresh_from_db()
    assert venda.situacao == Venda.Situacao.CONCLUIDA
    assert venda.troco == Decimal("10.00")
    # Depois do pagamento, a pessoa operadora continua no PDV, com a última venda à vista.
    assert resposta.status_code == 302
    assert resposta.url == reverse("vendas:pdv")
    pdv = client.get(reverse("vendas:pdv"))
    assert pdv.context["venda"] is None
    assert pdv.context["ultima_venda"] == venda


def test_pagamento_fica_na_tela_do_pdv(client, caixa, voluntario, produto_com_saldo):
    venda = iniciar_ou_retomar_venda(voluntario)
    adicionar_item(venda=venda, produto=produto_com_saldo)
    client.force_login(voluntario)
    pdv = client.get(reverse("vendas:pdv")).content.decode()
    assert 'id="pdv-pagamento"' in pdv
    assert reverse("vendas:pagamento", args=[venda.pk]) in pdv
    # A antiga página de pagamento não existe mais: o endereço volta ao PDV.
    assert client.get(reverse("vendas:pagamento", args=[venda.pk])).url == reverse("vendas:pdv")


def test_quantia_insuficiente_mostra_erro_no_pdv(client, caixa, voluntario, produto_com_saldo):
    venda = iniciar_ou_retomar_venda(voluntario)
    adicionar_item(venda=venda, produto=produto_com_saldo)
    client.force_login(voluntario)
    resposta = client.post(
        reverse("vendas:pagamento", args=[venda.pk]),
        {"forma_pagamento": FormaPagamento.DINHEIRO, "valor_recebido": "10.00"},
    )
    assert resposta.status_code == 200
    assert resposta.templates[0].name == "vendas/pdv.html"
    assert resposta.context["formulario_pagamento"].errors
    venda.refresh_from_db()
    assert venda.situacao == Venda.Situacao.EM_ANDAMENTO


def test_pagamento_com_cartao_no_pdv_dispensa_troco(client, caixa, voluntario, produto_com_saldo):
    venda = iniciar_ou_retomar_venda(voluntario)
    adicionar_item(venda=venda, produto=produto_com_saldo)
    client.force_login(voluntario)
    pdv = client.get(reverse("vendas:pdv")).content.decode()
    assert 'value="credito"' in pdv and 'value="debito"' in pdv
    resposta = client.post(
        reverse("vendas:pagamento", args=[venda.pk]), {"forma_pagamento": FormaPagamento.CREDITO}
    )
    assert resposta.url == reverse("vendas:pdv")
    venda.refresh_from_db()
    assert venda.situacao == Venda.Situacao.CONCLUIDA
    assert (venda.forma_pagamento, venda.troco) == (FormaPagamento.CREDITO, Decimal("0.00"))


def test_pesquisa_por_nome_com_varios_resultados_lista_candidatos(client, caixa, voluntario, produto, bolsista):
    Produto.objects.create(
        codigo="CAN-02", nome="Caneca térmica", preco_unitario=Decimal("40.00"), criado_por=bolsista, alterado_por=bolsista
    )
    client.force_login(voluntario)
    resposta = client.post(reverse("vendas:adicionar_item"), {"termo": "caneca", "quantidade": "1"})
    assert resposta.status_code == 200
    assert len(resposta.context["candidatos"]) == 2
    assert not Venda.objects.exists()


def test_item_rejeitado_nao_cria_venda_vazia(client, caixa, voluntario, produto):
    client.force_login(voluntario)  # produto sem saldo
    client.post(reverse("vendas:adicionar_item"), {"termo": "CAN-01", "quantidade": "1"})
    assert not Venda.objects.exists()


def test_operador_nao_altera_venda_de_outro(client, caixa, voluntario, bolsista, produto_com_saldo):
    venda = iniciar_ou_retomar_venda(voluntario)
    item = adicionar_item(venda=venda, produto=produto_com_saldo)
    client.force_login(bolsista)
    assert client.post(reverse("vendas:remover_item", args=[item.pk])).status_code == 404
    pagamento = {"forma_pagamento": FormaPagamento.PIX}
    assert client.post(reverse("vendas:pagamento", args=[venda.pk]), pagamento).status_code == 404


def test_consulta_de_vendas_filtra_por_caixa(client, caixa, voluntario, produto_com_saldo):
    venda = iniciar_ou_retomar_venda(voluntario)
    adicionar_item(venda=venda, produto=produto_com_saldo)
    concluir_venda(venda=venda, forma_pagamento=FormaPagamento.PIX)
    client.force_login(voluntario)
    resposta = client.get(reverse("vendas:lista_vendas"), {"caixa": caixa.pk, "situacao": "concluida"})
    assert list(resposta.context["vendas"]) == [venda]


# Devolução (UC16) --------------------------------------------------------------


def _vender(usuario, *itens, forma=FormaPagamento.PIX, valor_recebido=None):
    venda = iniciar_ou_retomar_venda(usuario)
    for produto, quantidade in itens:
        adicionar_item(venda=venda, produto=produto, quantidade=quantidade)
    return concluir_venda(venda=venda, forma_pagamento=forma, valor_recebido=valor_recebido)


def test_devolucao_estorna_pela_mesma_forma_e_recompoe_estoque(caixa, voluntario, produto_com_saldo, servico):
    venda = _vender(voluntario, (produto_com_saldo, 3), (servico, 4))
    item_caneca = venda.itens.get(produto=produto_com_saldo)
    item_servico = venda.itens.get(produto=servico)

    devolucao = registrar_devolucao(
        venda=venda,
        quantidades={item_caneca.pk: 2, item_servico.pk: 1},
        motivo="Defeito",
        usuario=voluntario,
    )

    assert devolucao.forma_estorno == FormaPagamento.PIX
    assert devolucao.valor_estornado == Decimal("60.25")
    produto_com_saldo.refresh_from_db()
    assert produto_com_saldo.saldo_estoque == 4  # 5 − 3 vendidas + 2 devolvidas
    recomposicao = Movimentacao.objects.get(tipo=Movimentacao.Tipo.DEVOLUCAO)
    assert recomposicao.variacao == 2
    venda.refresh_from_db()
    assert venda.total_liquido == Decimal("30.75")


def test_devolucoes_parciais_respeitam_o_que_foi_vendido(caixa, voluntario, produto_com_saldo):
    venda = _vender(voluntario, (produto_com_saldo, 2))
    item = venda.itens.get()
    registrar_devolucao(venda=venda, quantidades={item.pk: 1}, motivo="Troca", usuario=voluntario)
    with pytest.raises(ValidationError):
        registrar_devolucao(venda=venda, quantidades={item.pk: 2}, motivo="Troca", usuario=voluntario)
    registrar_devolucao(venda=venda, quantidades={item.pk: 1}, motivo="Troca", usuario=voluntario)
    assert motivo_devolucao_bloqueada(venda) == "Todos os itens desta venda já foram devolvidos."


@pytest.mark.parametrize(
    ("quantidades", "motivo"),
    [("nenhum item", "Defeito"), ("quantidade zero", "Defeito"), ("um item", "   ")],
)
def test_devolucao_invalida_nao_registra_nada(caixa, voluntario, produto_com_saldo, quantidades, motivo):
    venda = _vender(voluntario, (produto_com_saldo, 1))
    item = venda.itens.get()
    quantidades = {"nenhum item": {}, "quantidade zero": {item.pk: 0}, "um item": {item.pk: 1}}[quantidades]
    with pytest.raises(ValidationError):
        registrar_devolucao(venda=venda, quantidades=quantidades, motivo=motivo, usuario=voluntario)
    assert not Devolucao.objects.exists()
    assert not Movimentacao.objects.filter(tipo=Movimentacao.Tipo.DEVOLUCAO).exists()


def test_devolucao_fora_do_prazo_e_bloqueada(caixa, voluntario, produto_com_saldo, settings):
    venda = _vender(voluntario, (produto_com_saldo, 1))
    Venda.objects.filter(pk=venda.pk).update(
        concluida_em=timezone.now() - timedelta(days=settings.PRAZO_DEVOLUCAO_DIAS, minutes=1)
    )
    venda.refresh_from_db()
    with pytest.raises(ValidationError):
        registrar_devolucao(venda=venda, quantidades={venda.itens.get().pk: 1}, motivo="x", usuario=voluntario)


def test_devolucao_exige_caixa_aberto(caixa, voluntario, produto_com_saldo):
    venda = _vender(voluntario, (produto_com_saldo, 1))
    fechar_caixa(caixa=caixa, usuario=voluntario, valor_contado=Decimal("50.00"))
    assert "Abra o caixa" in motivo_devolucao_bloqueada(venda)


def test_estorno_em_dinheiro_sai_do_valor_esperado_do_caixa(caixa, voluntario, produto_com_saldo):
    venda = _vender(
        voluntario, (produto_com_saldo, 2), forma=FormaPagamento.DINHEIRO, valor_recebido=Decimal("60.00")
    )
    registrar_devolucao(venda=venda, quantidades={venda.itens.get().pk: 1}, motivo="Defeito", usuario=voluntario)
    resumo = resumir_caixa(caixa)
    assert resumo["valor_esperado"] == Decimal("80.00")  # 50 + 60 − 30
    assert (resumo["total_estornado"], resumo["total_liquido"]) == (Decimal("30.00"), Decimal("30.00"))


def test_devolucao_pela_tela_exige_confirmacao(client, caixa, voluntario, produto_com_saldo):
    venda = _vender(voluntario, (produto_com_saldo, 2))
    item = venda.itens.get()
    client.force_login(voluntario)
    url = reverse("vendas:registrar_devolucao", args=[venda.pk])
    dados = {f"item_{item.pk}": "1", "motivo": "Sabor errado"}

    resumo = client.post(url, dados)
    assert resumo.status_code == 200
    assert resumo.context["valor"] == Decimal("30.00")
    assert not Devolucao.objects.exists()

    confirmado = client.post(url, {**dados, "confirmar": "1"})
    assert confirmado.status_code == 302
    assert Devolucao.objects.get().valor_estornado == Decimal("30.00")


def test_tela_rejeita_quantidade_maior_que_a_vendida(client, caixa, voluntario, produto_com_saldo):
    venda = _vender(voluntario, (produto_com_saldo, 1))
    client.force_login(voluntario)
    resposta = client.post(
        reverse("vendas:registrar_devolucao", args=[venda.pk]),
        {f"item_{venda.itens.get().pk}": "2", "motivo": "x", "confirmar": "1"},
    )
    assert resposta.status_code == 200
    assert resposta.context["formulario"].errors
    assert not Devolucao.objects.exists()


def test_venda_cancelada_nao_aceita_devolucao(client, caixa, voluntario, produto_com_saldo):
    venda = iniciar_ou_retomar_venda(voluntario)
    adicionar_item(venda=venda, produto=produto_com_saldo)
    cancelar_venda(venda=venda)
    client.force_login(voluntario)
    resposta = client.get(reverse("vendas:registrar_devolucao", args=[venda.pk]))
    assert resposta.status_code == 302


# Relatório de vendas (UC50) ------------------------------------------------------


def test_relatorio_considera_so_vendas_concluidas_e_desconta_devolucoes(caixa, voluntario, produto_com_saldo):
    venda = _vender(voluntario, (produto_com_saldo, 2))
    registrar_devolucao(venda=venda, quantidades={venda.itens.get().pk: 1}, motivo="Defeito", usuario=voluntario)
    em_andamento = iniciar_ou_retomar_venda(voluntario)
    adicionar_item(venda=em_andamento, produto=produto_com_saldo)

    relatorio = gerar_relatorio_vendas(caixa=caixa.pk)
    assert relatorio["vendas"] == [venda]
    assert relatorio["total_vendido"] == Decimal("60.00")
    assert relatorio["total_estornado"] == Decimal("30.00")
    assert relatorio["total_liquido"] == Decimal("30.00")


def test_relatorio_usa_os_filtros_da_consulta(client, caixa, voluntario, produto_com_saldo):
    _vender(voluntario, (produto_com_saldo, 1))
    client.force_login(voluntario)
    resposta = client.get(reverse("vendas:relatorio_vendas"), {"caixa": caixa.pk})
    assert resposta.status_code == 200
    assert resposta.context["relatorio"]["quantidade_vendas"] == 1
    invalida = client.get(reverse("vendas:relatorio_vendas"), {"inicio": "2026-10-10", "fim": "2026-10-01"})
    assert invalida.status_code == 302
