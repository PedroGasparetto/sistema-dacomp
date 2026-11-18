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

PREPARO = "Preparo próprio"
PARCEIRO = "Padaria parceira (exemplo)"
COPO = Produto.Unidade.COPO
FATIA = Produto.Unidade.FATIA

# Códigos de barras com prefixo 2 (uso interno), para não coincidirem com produtos reais.
PRODUTOS_DEMO = [
    # código, nome, categoria, venda, custo, controla estoque, saldo inicial, extras
    ("CAF-P", "Café coado (pequeno)", Categoria.CAFE, "2.50", "0.60", False, 0, {"fornecedor": PREPARO, "unidade": COPO}),
    ("CAF-G", "Café coado (grande)", Categoria.CAFE, "4.00", "1.00", False, 0, {"fornecedor": PREPARO, "unidade": COPO}),
    ("CAF-LEI", "Café com leite", Categoria.CAFE, "4.50", "1.30", False, 0, {"fornecedor": PREPARO, "unidade": COPO}),
    ("CHA-01", "Chá (sachê)", Categoria.CAFE, "2.00", "0.50", True, 40, {}),
    ("CHOC-Q", "Chocolate quente", Categoria.CAFE, "5.00", "1.60", False, 0, {"fornecedor": PREPARO, "unidade": COPO}),
    ("REF-LAT", "Refrigerante lata 350 ml", Categoria.BEBIDA, "5.00", "2.60", True, 48,
     {"codigo_barras": "2000000000015"}),
    ("AGU-500", "Água mineral 500 ml", Categoria.BEBIDA, "3.00", "1.10", True, 36,
     {"codigo_barras": "2000000000022"}),
    ("AGU-GAS", "Água com gás 500 ml", Categoria.BEBIDA, "3.50", "1.40", True, 4,
     {"codigo_barras": "2000000000039"}),
    ("SUC-CX", "Suco de caixinha 200 ml", Categoria.BEBIDA, "3.50", "1.70", True, 24,
     {"codigo_barras": "2000000000046"}),
    ("ENE-LAT", "Energético lata 250 ml", Categoria.BEBIDA, "9.00", "5.20", True, 0,
     {"codigo_barras": "2000000000053"}),
    ("SAL-ASS", "Salgado assado", Categoria.LANCHE, "6.00", "3.50", True, 20, {"fornecedor": PARCEIRO}),
    ("PAO-QJ", "Pão de queijo", Categoria.LANCHE, "3.00", "1.40", True, 30, {"fornecedor": PARCEIRO}),
    ("SAN-NAT", "Sanduíche natural", Categoria.LANCHE, "8.00", "4.80", True, 8, {"fornecedor": PARCEIRO}),
    ("BIS-REC", "Biscoito recheado", Categoria.LANCHE, "4.00", "2.10", True, 18,
     {"codigo_barras": "2000000000060"}),
    ("CHO-BAR", "Chocolate em barra", Categoria.DOCE, "6.00", "3.40", True, 15,
     {"codigo_barras": "2000000000077"}),
    ("BOL-FAT", "Fatia de bolo", Categoria.DOCE, "5.00", "2.50", True, 10, {"fornecedor": PARCEIRO, "unidade": FATIA}),
    ("BRI-01", "Brigadeiro", Categoria.DOCE, "2.50", "1.00", True, 25, {"fornecedor": PARCEIRO}),
    ("PAC-01", "Paçoca", Categoria.DOCE, "1.00", "0.40", True, 50, {"codigo_barras": "2000000000084"}),
    ("IMP-PB", "Impressão preto e branco (página)", Categoria.OUTRO, "0.25", "0.08", False, 0, {}),
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
        for (
            codigo, nome, categoria, preco, custo, controla_estoque, saldo_inicial, extras
        ) in PRODUTOS_DEMO:
            produto, criado = Produto.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "nome": nome,
                    "categoria": categoria,
                    "preco_unitario": Decimal(preco),
                    "preco_custo": Decimal(custo),
                    "controla_estoque": controla_estoque,
                    "criado_por": autor,
                    "alterado_por": autor,
                    **extras,
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
