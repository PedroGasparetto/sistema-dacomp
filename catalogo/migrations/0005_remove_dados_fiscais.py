from decimal import Decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    """Retira os dados fiscais do produto e mantém só a unidade de venda."""

    dependencies = [
        ("catalogo", "0004_produto_cest_produto_cfop_produto_csosn_and_more"),
    ]

    operations = [
        migrations.RemoveField(model_name="produto", name="ncm"),
        migrations.RemoveField(model_name="produto", name="cest"),
        migrations.RemoveField(model_name="produto", name="cfop"),
        migrations.RemoveField(model_name="produto", name="origem"),
        migrations.RemoveField(model_name="produto", name="csosn"),
        migrations.RenameField(model_name="produto", old_name="unidade_comercial", new_name="unidade"),
        migrations.AlterField(
            model_name="produto",
            name="unidade",
            field=models.CharField(
                choices=[
                    ("UN", "Unidade"),
                    ("COPO", "Copo"),
                    ("FATIA", "Fatia"),
                    ("PCT", "Pacote"),
                    ("CX", "Caixa"),
                    ("DZ", "Dúzia"),
                    ("KG", "Quilo"),
                    ("L", "Litro"),
                ],
                default="UN",
                max_length=5,
                verbose_name="unidade de venda",
            ),
        ),
        migrations.AlterField(
            model_name="produto",
            name="codigo_barras",
            field=models.CharField(
                blank=True,
                help_text="Opcional; permite identificar o item com o leitor de código de barras.",
                max_length=50,
                null=True,
                unique=True,
                verbose_name="código de barras",
            ),
        ),
        migrations.AlterField(
            model_name="produto",
            name="preco_custo",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Quanto a lojinha paga por unidade; usado para calcular o lucro.",
                max_digits=8,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                verbose_name="preço de custo",
            ),
        ),
    ]
