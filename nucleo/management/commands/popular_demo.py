"""Cria contas e produtos de demonstração para desenvolvimento e apresentação."""

from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from catalogo.models import Produto
from contas.models import Usuario
from contas.perfis import BOLSISTA, DIRETORIA, VOLUNTARIO
from estoque.models import Movimentacao
from estoque.servicos import registrar_movimentacao

USUARIOS_DEMO = [
    ("diretoria", "Diana", "Diretoria", [DIRETORIA]),
    ("bolsista", "Bruno", "Bolsista", [BOLSISTA]),
    ("voluntario", "Vera", "Voluntária", [VOLUNTARIO]),
]

# código, nome, preço, controla estoque, código de barras, saldo inicial
PRODUTOS_DEMO = [
    ("CAM-P", "Camiseta da Computação (P)", "45.00", True, "7890000000017", 12),
    ("CAM-M", "Camiseta da Computação (M)", "45.00", True, "7890000000024", 20),
    ("MOL-G", "Moletom da Computação (G)", "120.00", True, "7890000000031", 6),
    ("CAN-01", "Caneca do DACOMP", "30.00", True, "7890000000048", 15),
    ("ADS-01", "Adesivo do Instituto", "5.00", True, None, 80),
    ("CAF-01", "Café passado (copo)", "2.50", True, None, 0),
    ("IMP-PB", "Impressão preto e branco (página)", "0.25", False, None, 0),
    ("IMP-COR", "Impressão colorida (página)", "1.00", False, None, 0),
]


class Command(BaseCommand):
    help = "Cria as contas diretoria, bolsista e voluntario e um catálogo de exemplo."

    def add_arguments(self, parser):
        parser.add_argument("--senha", required=True, help="Senha das contas de demonstração.")

    @transaction.atomic
    def handle(self, *args, senha, **options):
        for username, nome, sobrenome, perfis in USUARIOS_DEMO:
            usuario, criado = Usuario.objects.get_or_create(
                username=username, defaults={"first_name": nome, "last_name": sobrenome}
            )
            usuario.set_password(senha)
            usuario.save()
            usuario.groups.set(Group.objects.filter(name__in=perfis))
            self.stdout.write(f"{'Criada' if criado else 'Atualizada'} a conta {username}")

        autor = Usuario.objects.get(username="bolsista")
        for codigo, nome, preco, controla_estoque, codigo_barras, saldo_inicial in PRODUTOS_DEMO:
            produto, criado = Produto.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "nome": nome,
                    "preco_unitario": Decimal(preco),
                    "controla_estoque": controla_estoque,
                    "codigo_barras": codigo_barras,
                    "criado_por": autor,
                    "alterado_por": autor,
                },
            )
            if criado and saldo_inicial:
                registrar_movimentacao(
                    tipo=Movimentacao.Tipo.ENTRADA,
                    produto=produto,
                    quantidade=saldo_inicial,
                    usuario=autor,
                    observacao="Saldo inicial da demonstração",
                )
        self.stdout.write(self.style.SUCCESS("Dados de demonstração prontos."))
