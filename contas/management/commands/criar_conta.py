"""Cria uma conta da equipe ou atualiza seus perfis pela linha de comando.

Exemplos:
    python manage.py criar_conta ana --perfil diretoria --nome Ana
    python manage.py criar_conta bruno --perfil bolsista --perfil diretoria
    python manage.py criar_conta vera --desativar

Para trocar a senha de uma conta existente: python manage.py changepassword <usuário>
"""

import getpass
import unicodedata

from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from contas.models import Usuario
from contas.perfis import TODOS_PERFIS


def _sem_acento(texto):
    return "".join(
        c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn"
    )


# Aceita "voluntario", "Voluntário", "DIRETORIA" etc.
PERFIS_POR_CHAVE = {_sem_acento(perfil): perfil for perfil in TODOS_PERFIS}


class Command(BaseCommand):
    help = "Cria uma conta da equipe ou atualiza seus perfis (Diretoria, Bolsista, Voluntário)."

    def add_arguments(self, parser):
        parser.add_argument("username", help="Nome de usuário usado no login.")
        parser.add_argument(
            "--perfil",
            action="append",
            dest="perfis",
            default=[],
            help="Perfil da conta; repita para acumular papéis. Opções: diretoria, bolsista, voluntario.",
        )
        parser.add_argument("--nome", default=None, help="Primeiro nome.")
        parser.add_argument("--sobrenome", default=None, help="Sobrenome.")
        parser.add_argument("--email", default=None, help="E-mail.")
        parser.add_argument(
            "--senha",
            default=None,
            help="Senha da conta nova. Sem esta opção, a senha é pedida no terminal.",
        )
        situacao = parser.add_mutually_exclusive_group()
        situacao.add_argument("--desativar", action="store_true", help="Impede o login da conta.")
        situacao.add_argument("--reativar", action="store_true", help="Volta a permitir o login.")

    def handle(self, *args, username, perfis, nome, sobrenome, email, senha, desativar, reativar, **options):
        perfis = self._resolver_perfis(perfis)
        conta = Usuario.objects.filter(username=username).first()

        if conta is None:
            if not perfis:
                raise CommandError("Informe ao menos um --perfil para a conta nova.")
            senha = senha or self._pedir_senha()
            conta = Usuario(username=username)
            self._validar_senha(senha, conta)
            conta.set_password(senha)
        elif senha:
            raise CommandError(f"Para trocar a senha de {username}, use: manage.py changepassword {username}")

        for campo, valor in (("first_name", nome), ("last_name", sobrenome), ("email", email)):
            if valor is not None:
                setattr(conta, campo, valor)
        if desativar:
            conta.is_active = False
        if reativar:
            conta.is_active = True

        with transaction.atomic():
            criada = conta.pk is None
            conta.save()
            if perfis:
                conta.groups.set(Group.objects.filter(name__in=perfis))

        situacao = "ativa" if conta.is_active else "desativada"
        self.stdout.write(
            self.style.SUCCESS(
                f"Conta {username} {'criada' if criada else 'atualizada'} ({situacao}): "
                f"{', '.join(conta.nomes_perfis) or 'sem perfil'}."
            )
        )

    def _resolver_perfis(self, perfis):
        resolvidos = []
        for perfil in perfis:
            canonico = PERFIS_POR_CHAVE.get(_sem_acento(perfil))
            if canonico is None:
                raise CommandError(f"Perfil desconhecido: {perfil}. Use diretoria, bolsista ou voluntario.")
            resolvidos.append(canonico)
        return resolvidos

    def _pedir_senha(self):
        senha = getpass.getpass("Senha: ")
        if senha != getpass.getpass("Confirme a senha: "):
            raise CommandError("As senhas não conferem.")
        return senha

    def _validar_senha(self, senha, conta):
        try:
            validate_password(senha, conta)
        except ValidationError as erro:
            raise CommandError(" ".join(erro.messages)) from erro
