from decimal import Decimal

import pytest
from django.contrib.auth.models import Group

from catalogo.models import Produto
from contas.models import Usuario
from contas.perfis import BOLSISTA, DIRETORIA, VOLUNTARIO

SENHA_TESTE = "senha-de-teste-123"


def _criar_usuario(username, *perfis):
    usuario = Usuario.objects.create_user(username=username, password=SENHA_TESTE)
    usuario.groups.set(Group.objects.filter(name__in=perfis))
    return usuario


@pytest.fixture
def diretoria(db):
    return _criar_usuario("diretoria", DIRETORIA)


@pytest.fixture
def bolsista(db):
    return _criar_usuario("bolsista", BOLSISTA)


@pytest.fixture
def voluntario(db):
    return _criar_usuario("voluntario", VOLUNTARIO)


@pytest.fixture
def produto(bolsista):
    return Produto.objects.create(
        codigo="CAN-01",
        nome="Caneca do DACOMP",
        codigo_barras="7890000000048",
        preco_unitario=Decimal("30.00"),
        criado_por=bolsista,
        alterado_por=bolsista,
    )


@pytest.fixture
def servico(bolsista):
    return Produto.objects.create(
        codigo="IMP-PB",
        nome="Impressão preto e branco",
        preco_unitario=Decimal("0.25"),
        controla_estoque=False,
        criado_por=bolsista,
        alterado_por=bolsista,
    )
