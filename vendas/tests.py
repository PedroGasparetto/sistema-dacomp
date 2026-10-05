from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from catalogo.models import Produto
from estoque.models import Movimentacao
from estoque.servicos import registrar_movimentacao
from vendas.models import Caixa, Venda
from vendas.servicos import (
    abrir_caixa,
    adicionar_item,
    cancelar_venda,
    concluir_venda,
    fechar_caixa,
    iniciar_ou_retomar_venda,
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
    assert resposta.status_code == 302
    assert venda.situacao == Venda.Situacao.CONCLUIDA
    assert venda.troco == Decimal("10.00")


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
    assert client.get(reverse("vendas:pagamento", args=[venda.pk])).status_code == 404


def test_consulta_de_vendas_filtra_por_caixa(client, caixa, voluntario, produto_com_saldo):
    venda = iniciar_ou_retomar_venda(voluntario)
    adicionar_item(venda=venda, produto=produto_com_saldo)
    concluir_venda(venda=venda, forma_pagamento=FormaPagamento.PIX)
    client.force_login(voluntario)
    resposta = client.get(reverse("vendas:lista_vendas"), {"caixa": caixa.pk, "situacao": "concluida"})
    assert list(resposta.context["vendas"]) == [venda]
