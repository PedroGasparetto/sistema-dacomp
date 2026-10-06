import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import NoReverseMatch, reverse

from contas.models import Usuario
from contas.perfis import TODOS_PERFIS

SENHA_FORTE = "uma-senha-forte-456"


@pytest.mark.django_db
def test_perfis_sao_criados_pela_migracao():
    assert set(Group.objects.values_list("name", flat=True)) >= set(TODOS_PERFIS)


def test_visitante_e_redirecionado_para_login(client, db):
    resposta = client.get(reverse("nucleo:inicio"))
    assert resposta.status_code == 302
    assert reverse("contas:entrar") in resposta.url


def test_usuario_sem_perfil_nao_opera(client, db):
    usuario = Usuario.objects.create_user(username="sem-perfil", password="x")
    client.force_login(usuario)
    assert client.get(reverse("catalogo:lista_produtos")).status_code == 403


def test_gestao_de_contas_nao_tem_tela(client, diretoria):
    with pytest.raises(NoReverseMatch):
        reverse("contas:lista_contas")
    client.force_login(diretoria)
    assert client.get("/conta/usuarios/").status_code == 404


# Comando criar_conta -----------------------------------------------------------


@pytest.mark.django_db
def test_cria_conta_com_perfis_acumulados_e_sem_acento():
    call_command("criar_conta", "ana", perfis=["DIRETORIA", "voluntario"], nome="Ana", senha=SENHA_FORTE)
    conta = Usuario.objects.get(username="ana")
    assert conta.nomes_perfis == ["Diretoria", "Voluntário"]
    assert conta.first_name == "Ana"
    assert conta.check_password(SENHA_FORTE)


@pytest.mark.django_db
def test_conta_nova_exige_perfil_e_senha_valida():
    with pytest.raises(CommandError):
        call_command("criar_conta", "ana", senha=SENHA_FORTE)
    with pytest.raises(CommandError):
        call_command("criar_conta", "ana", perfis=["bolsista"], senha="123")
    with pytest.raises(CommandError):
        call_command("criar_conta", "ana", perfis=["gerente"], senha=SENHA_FORTE)
    assert not Usuario.objects.filter(username="ana").exists()


def test_atualiza_perfis_e_desativa_sem_mexer_na_senha(bolsista):
    senha_antes = bolsista.password
    call_command("criar_conta", "bolsista", perfis=["bolsista", "diretoria"])
    call_command("criar_conta", "bolsista", desativar=True)
    bolsista.refresh_from_db()
    assert bolsista.nomes_perfis == ["Diretoria", "Bolsista"]
    assert not bolsista.is_active
    assert bolsista.password == senha_antes


def test_troca_de_senha_fica_com_changepassword(bolsista):
    with pytest.raises(CommandError):
        call_command("criar_conta", "bolsista", senha=SENHA_FORTE)
