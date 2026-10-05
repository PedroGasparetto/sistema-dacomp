import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from contas.models import Usuario
from contas.perfis import DIRETORIA, TODOS_PERFIS


@pytest.mark.django_db
def test_perfis_sao_criados_pela_migracao():
    assert set(Group.objects.values_list("name", flat=True)) >= set(TODOS_PERFIS)


def test_visitante_e_redirecionado_para_login(client, db):
    resposta = client.get(reverse("nucleo:inicio"))
    assert resposta.status_code == 302
    assert reverse("contas:entrar") in resposta.url


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
            "password1": "uma-senha-forte-456",
            "password2": "uma-senha-forte-456",
            "perfis": [perfil.pk for perfil in perfis],
        },
    )
    assert resposta.status_code == 302
    assert Usuario.objects.get(username="nova").nomes_perfis == ["Diretoria", "Bolsista"]


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


def test_usuario_sem_perfil_nao_opera(client, db):
    usuario = Usuario.objects.create_user(username="sem-perfil", password="x")
    client.force_login(usuario)
    assert client.get(reverse("catalogo:lista_produtos")).status_code == 403
