import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from estoque.models import Movimentacao
from estoque.servicos import filtrar_movimentacoes, registrar_movimentacao

Tipo = Movimentacao.Tipo
Motivo = Movimentacao.MotivoAjuste


def test_entrada_soma_quantidade_e_registra_historico(produto, voluntario):
    movimentacao = registrar_movimentacao(tipo=Tipo.ENTRADA, produto=produto, quantidade=10, usuario=voluntario)
    produto.refresh_from_db()
    assert produto.saldo_estoque == 10
    assert (
        movimentacao.quantidade_anterior,
        movimentacao.variacao,
        movimentacao.quantidade_resultante,
    ) == (0, 10, 10)
    assert movimentacao.responsavel == voluntario


def test_ajuste_substitui_saldo_pela_contagem(produto, voluntario):
    registrar_movimentacao(tipo=Tipo.ENTRADA, produto=produto, quantidade=10, usuario=voluntario)
    movimentacao = registrar_movimentacao(
        tipo=Tipo.AJUSTE, produto=produto, quantidade=7, motivo=Motivo.AVARIA, usuario=voluntario
    )
    produto.refresh_from_db()
    assert produto.saldo_estoque == 7
    assert movimentacao.variacao == -3


@pytest.mark.parametrize(
    ("tipo", "quantidade", "motivo", "campo"),
    [
        (Tipo.ENTRADA, 0, "", "quantidade"),
        (Tipo.AJUSTE, 5, "", "motivo"),
        (Tipo.AJUSTE, 0, Motivo.PERDA, "quantidade"),  # igual ao saldo atual
        (Tipo.AJUSTE, -1, Motivo.PERDA, "quantidade"),
    ],
)
def test_movimentacoes_invalidas_sao_rejeitadas(produto, voluntario, tipo, quantidade, motivo, campo):
    with pytest.raises(ValidationError) as erro:
        registrar_movimentacao(
            tipo=tipo, produto=produto, quantidade=quantidade, motivo=motivo, usuario=voluntario
        )
    assert campo in erro.value.message_dict
    produto.refresh_from_db()
    assert produto.saldo_estoque == 0
    assert not Movimentacao.objects.exists()


def test_entrada_bloqueada_para_produto_inativo(produto, voluntario):
    produto.ativo = False
    produto.save()
    with pytest.raises(ValidationError):
        registrar_movimentacao(tipo=Tipo.ENTRADA, produto=produto, quantidade=1, usuario=voluntario)


def test_ajuste_permitido_para_produto_inativo(produto, voluntario):
    registrar_movimentacao(tipo=Tipo.ENTRADA, produto=produto, quantidade=2, usuario=voluntario)
    produto.refresh_from_db()
    produto.ativo = False
    produto.save(update_fields=["ativo"])
    registrar_movimentacao(tipo=Tipo.AJUSTE, produto=produto, quantidade=0, motivo=Motivo.PERDA, usuario=voluntario)
    produto.refresh_from_db()
    assert produto.saldo_estoque == 0


def test_servico_sem_controle_de_estoque_e_rejeitado(servico, voluntario):
    with pytest.raises(ValidationError):
        registrar_movimentacao(tipo=Tipo.ENTRADA, produto=servico, quantidade=1, usuario=voluntario)


def test_registro_exige_confirmacao(client, voluntario, produto):
    client.force_login(voluntario)
    url = reverse("estoque:registrar_movimentacao")
    dados = {"tipo": Tipo.ENTRADA, "produto": "7890000000048", "quantidade": "4"}

    resumo = client.post(url, dados)
    assert resumo.status_code == 200
    assert resumo.context["quantidade_resultante"] == 4
    assert not Movimentacao.objects.exists()

    confirmado = client.post(url, {**dados, "confirmar": "1"})
    movimentacao = Movimentacao.objects.get()
    assert confirmado.status_code == 302
    assert confirmado.url == movimentacao.get_absolute_url()
    produto.refresh_from_db()
    assert produto.saldo_estoque == 4


def test_formulario_mostra_erros_de_regra(client, voluntario, produto):
    client.force_login(voluntario)
    resposta = client.post(
        reverse("estoque:registrar_movimentacao"),
        {"tipo": Tipo.AJUSTE, "produto": "CAN-01", "quantidade": "3"},
    )
    assert resposta.status_code == 200
    assert "motivo" in resposta.context["form"].errors


def test_filtro_por_produto_e_tipo(produto, servico, voluntario):
    registrar_movimentacao(tipo=Tipo.ENTRADA, produto=produto, quantidade=5, usuario=voluntario)
    registrar_movimentacao(tipo=Tipo.AJUSTE, produto=produto, quantidade=4, motivo=Motivo.PERDA, usuario=voluntario)
    assert filtrar_movimentacoes(termo_produto="caneca").count() == 2
    assert filtrar_movimentacoes(termo_produto="can-01", tipo=Tipo.AJUSTE).count() == 1
    assert filtrar_movimentacoes(termo_produto="impressão").count() == 0


def test_lista_rejeita_periodo_invertido(client, voluntario):
    client.force_login(voluntario)
    resposta = client.get(
        reverse("estoque:lista_movimentacoes"), {"inicio": "2026-10-10", "fim": "2026-10-01"}
    )
    assert resposta.status_code == 200
    assert resposta.context["formulario_filtro"].errors
