from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from django.utils import timezone

from contas.models import Usuario
from contas.perfis import DIRETORIA, TODOS_PERFIS
from contas.turno import CHAVE_INICIO_TURNO

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


# UC15 – Manter Contas ------------------------------------------------------------


def test_gestao_de_contas_e_exclusiva_da_diretoria(client, bolsista, diretoria):
    client.force_login(bolsista)
    assert client.get(reverse("contas:lista_contas")).status_code == 403
    client.force_login(diretoria)
    assert client.get(reverse("contas:lista_contas")).status_code == 200


def test_diretoria_cria_conta_com_perfis_acumulados(client, diretoria):
    client.force_login(diretoria)
    perfis = Group.objects.filter(name__in=["Diretoria", "Bolsista"])
    resposta = client.post(
        reverse("contas:criar_conta"),
        {
            "username": "nova",
            "first_name": "Nova",
            "last_name": "Pessoa",
            "email": "nova@inf.ufrgs.br",
            "password1": SENHA_FORTE,
            "password2": SENHA_FORTE,
            "perfis": [perfil.pk for perfil in perfis],
        },
    )
    assert resposta.status_code == 302
    assert Usuario.objects.get(username="nova").nomes_perfis == ["Diretoria", "Bolsista"]


def test_diretoria_inativa_conta(client, diretoria, voluntario):
    client.force_login(diretoria)
    perfil = Group.objects.get(name="Voluntário")
    resposta = client.post(
        reverse("contas:editar_conta", args=[voluntario.pk]), {"perfis": [perfil.pk]}
    )
    assert resposta.status_code == 302
    voluntario.refresh_from_db()
    assert not voluntario.is_active


def test_diretoria_nao_remove_o_proprio_perfil_de_diretoria(client, diretoria):
    client.force_login(diretoria)
    perfil_bolsista = Group.objects.get(name="Bolsista")
    resposta = client.post(
        reverse("contas:editar_conta", args=[diretoria.pk]),
        {"is_active": "on", "perfis": [perfil_bolsista.pk]},
    )
    assert resposta.status_code == 200
    diretoria.refresh_from_db()
    assert DIRETORIA in diretoria.nomes_perfis


def test_diretoria_redefine_senha(client, diretoria, voluntario):
    client.force_login(diretoria)
    resposta = client.post(
        reverse("contas:redefinir_senha", args=[voluntario.pk]),
        {"new_password1": SENHA_FORTE, "new_password2": SENHA_FORTE},
    )
    assert resposta.status_code == 302
    voluntario.refresh_from_db()
    assert voluntario.check_password(SENHA_FORTE)


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


# Sessão por turno ----------------------------------------------------------------


def test_login_inicia_o_turno(client, voluntario):
    client.force_login(voluntario)
    assert CHAVE_INICIO_TURNO in client.session
    resposta = client.get(reverse("nucleo:inicio"))
    assert resposta.status_code == 200
    assert resposta.context["fim_do_turno"] is not None


def test_fim_do_turno_encerra_a_sessao(client, voluntario, settings):
    client.force_login(voluntario)
    sessao = client.session
    sessao[CHAVE_INICIO_TURNO] = (
        timezone.now() - timedelta(minutes=settings.DURACAO_TURNO_MINUTOS, seconds=1)
    ).timestamp()
    sessao.save()

    resposta = client.get(reverse("vendas:pdv"))
    assert resposta.status_code == 302
    assert resposta.url.startswith(reverse("contas:entrar"))
    assert "next=" in resposta.url
    # Sem login, a próxima tela também pede autenticação.
    assert client.get(reverse("nucleo:inicio")).status_code == 302


def test_sessao_termina_ao_fechar_o_navegador(settings):
    assert settings.SESSION_EXPIRE_AT_BROWSER_CLOSE
    assert settings.SESSION_COOKIE_AGE == settings.DURACAO_TURNO_MINUTOS * 60


def test_diretoria_nao_altera_conta_de_superusuario(client, diretoria):
    raiz = Usuario.objects.create_superuser("raiz", password="senha-original-123")
    client.force_login(diretoria)
    nova = {"new_password1": SENHA_FORTE, "new_password2": SENHA_FORTE}
    assert client.post(reverse("contas:redefinir_senha", args=[raiz.pk]), nova).status_code == 404
    assert client.post(reverse("contas:editar_conta", args=[raiz.pk]), {"is_active": ""}).status_code == 404
    assert "raiz" not in client.get(reverse("contas:lista_contas")).content.decode()
    raiz.refresh_from_db()
    assert raiz.is_active and raiz.check_password("senha-original-123")
