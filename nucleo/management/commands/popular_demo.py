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

Categoria = Produto.Categoria

# código, nome, categoria, preço, controla estoque, código de barras, saldo inicial
PRODUTOS_DEMO = [
    ("CAF-P", "Café coado (pequeno)", Categoria.CAFE, "2.50", False, None, 0),
    ("CAF-G", "Café coado (grande)", Categoria.CAFE, "4.00", False, None, 0),
    ("CAF-LEI", "Café com leite", Categoria.CAFE, "4.50", False, None, 0),
    ("CHA-01", "Chá (sachê)", Categoria.CAFE, "2.00", True, None, 40),
    ("CHOC-Q", "Chocolate quente", Categoria.CAFE, "5.00", False, None, 0),
    ("REF-LAT", "Refrigerante lata 350 ml", Categoria.BEBIDA, "5.00", True, "7894900011517", 48),
    ("AGU-500", "Água mineral 500 ml", Categoria.BEBIDA, "3.00", True, "7896065200019", 36),
    ("AGU-GAS", "Água com gás 500 ml", Categoria.BEBIDA, "3.50", True, "7896065200026", 12),
    ("SUC-CX", "Suco de caixinha 200 ml", Categoria.BEBIDA, "3.50", True, "7891098000019", 24),
    ("ENE-LAT", "Energético lata 250 ml", Categoria.BEBIDA, "9.00", True, "9002490100070", 0),
    ("SAL-ASS", "Salgado assado", Categoria.LANCHE, "6.00", True, None, 20),
    ("PAO-QJ", "Pão de queijo", Categoria.LANCHE, "3.00", True, None, 30),
    ("SAN-NAT", "Sanduíche natural", Categoria.LANCHE, "8.00", True, None, 8),
    ("BIS-REC", "Biscoito recheado", Categoria.LANCHE, "4.00", True, "7896004000014", 18),
    ("CHO-BAR", "Chocolate em barra", Categoria.DOCE, "6.00", True, "7891000100103", 15),
    ("BOL-FAT", "Fatia de bolo", Categoria.DOCE, "5.00", True, None, 10),
    ("BRI-01", "Brigadeiro", Categoria.DOCE, "2.50", True, None, 25),
    ("PAC-01", "Paçoca", Categoria.DOCE, "1.00", True, "7896336000010", 50),
    ("IMP-PB", "Impressão preto e branco (página)", Categoria.OUTRO, "0.25", False, None, 0),
]


class Command(BaseCommand):
    help = "Cria as contas diretoria, bolsista e voluntario e um cardápio de bar e café de exemplo."

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
        for codigo, nome, categoria, preco, controla_estoque, codigo_barras, saldo_inicial in PRODUTOS_DEMO:
            produto, criado = Produto.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "nome": nome,
                    "categoria": categoria,
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
