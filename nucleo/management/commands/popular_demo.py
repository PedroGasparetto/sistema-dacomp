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

# Códigos de barras com prefixo 2 (uso interno), para não coincidirem com produtos reais.
# NCM preenchido apenas em itens industrializados; a classificação fiscal deve ser
# confirmada com a contabilidade do DACOMP.
PRODUTOS_DEMO = [
    # código, nome, categoria, venda, custo, controla estoque, mínimo, saldo inicial, extras
    ("CAF-P", "Café coado (pequeno)", Categoria.CAFE, "2.50", "0.60", False, 0, 0, {"fornecedor": PREPARO}),
    ("CAF-G", "Café coado (grande)", Categoria.CAFE, "4.00", "1.00", False, 0, 0, {"fornecedor": PREPARO}),
    ("CAF-LEI", "Café com leite", Categoria.CAFE, "4.50", "1.30", False, 0, 0, {"fornecedor": PREPARO}),
    ("CHA-01", "Chá (sachê)", Categoria.CAFE, "2.00", "0.50", True, 10, 40, {"ncm": "09023000"}),
    ("CHOC-Q", "Chocolate quente", Categoria.CAFE, "5.00", "1.60", False, 0, 0, {"fornecedor": PREPARO}),
    ("REF-LAT", "Refrigerante lata 350 ml", Categoria.BEBIDA, "5.00", "2.60", True, 12, 48,
     {"codigo_barras": "2000000000015", "ncm": "22021000"}),
    ("AGU-500", "Água mineral 500 ml", Categoria.BEBIDA, "3.00", "1.10", True, 12, 36,
     {"codigo_barras": "2000000000022", "ncm": "22011000"}),
    ("AGU-GAS", "Água com gás 500 ml", Categoria.BEBIDA, "3.50", "1.40", True, 6, 4,
     {"codigo_barras": "2000000000039", "ncm": "22011000"}),
    ("SUC-CX", "Suco de caixinha 200 ml", Categoria.BEBIDA, "3.50", "1.70", True, 12, 24,
     {"codigo_barras": "2000000000046", "ncm": "22029900"}),
    ("ENE-LAT", "Energético lata 250 ml", Categoria.BEBIDA, "9.00", "5.20", True, 6, 0,
     {"codigo_barras": "2000000000053", "ncm": "22029900"}),
    ("SAL-ASS", "Salgado assado", Categoria.LANCHE, "6.00", "3.50", True, 10, 20, {"fornecedor": PARCEIRO}),
    ("PAO-QJ", "Pão de queijo", Categoria.LANCHE, "3.00", "1.40", True, 10, 30, {"fornecedor": PARCEIRO}),
    ("SAN-NAT", "Sanduíche natural", Categoria.LANCHE, "8.00", "4.80", True, 5, 8, {"fornecedor": PARCEIRO}),
    ("BIS-REC", "Biscoito recheado", Categoria.LANCHE, "4.00", "2.10", True, 6, 18,
     {"codigo_barras": "2000000000060", "ncm": "19053100"}),
    ("CHO-BAR", "Chocolate em barra", Categoria.DOCE, "6.00", "3.40", True, 6, 15,
     {"codigo_barras": "2000000000077", "ncm": "18063210"}),
    ("BOL-FAT", "Fatia de bolo", Categoria.DOCE, "5.00", "2.50", True, 4, 10, {"fornecedor": PARCEIRO}),
    ("BRI-01", "Brigadeiro", Categoria.DOCE, "2.50", "1.00", True, 10, 25, {"fornecedor": PARCEIRO}),
    ("PAC-01", "Paçoca", Categoria.DOCE, "1.00", "0.40", True, 20, 50, {"codigo_barras": "2000000000084"}),
    ("IMP-PB", "Impressão preto e branco (página)", Categoria.OUTRO, "0.25", "0.08", False, 0, 0, {}),
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
            codigo, nome, categoria, preco, custo, controla_estoque, minimo, saldo_inicial, extras
        ) in PRODUTOS_DEMO:
            produto, criado = Produto.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "nome": nome,
                    "categoria": categoria,
                    "preco_unitario": Decimal(preco),
                    "preco_custo": Decimal(custo),
                    "controla_estoque": controla_estoque,
                    "estoque_minimo": minimo,
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
