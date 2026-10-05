from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


class Produto(models.Model):
    """Produto ou serviço oferecido pela lojinha (seção C.3 do relatório).

    A maior parte do catálogo é de bar e café: bebidas, lanches e doces.
    O saldo em estoque não é editável pelo cadastro: ele só muda pelas
    movimentações de estoque (app `estoque`).
    """

    class Categoria(models.TextChoices):
        CAFE = "cafe", "Cafés e bebidas quentes"
        BEBIDA = "bebida", "Bebidas"
        LANCHE = "lanche", "Lanches e salgados"
        DOCE = "doce", "Doces"
        OUTRO = "outro", "Outros"

    codigo = models.CharField("código interno", max_length=20, unique=True)
    nome = models.CharField("nome", max_length=120)
    categoria = models.CharField(
        "categoria", max_length=10, choices=Categoria.choices, default=Categoria.OUTRO
    )
    descricao = models.TextField("descrição", blank=True)
    codigo_barras = models.CharField(
        "código de barras", max_length=50, unique=True, null=True, blank=True
    )
    preco_unitario = models.DecimalField(
        "preço unitário",
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    ativo = models.BooleanField("ativo", default=True)
    controla_estoque = models.BooleanField(
        "controla estoque",
        default=True,
        help_text="Desmarque para itens preparados na hora (como café coado) e para serviços.",
    )
    saldo_estoque = models.PositiveIntegerField("saldo em estoque", default=0, editable=False)

    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name="criado por",
    )
    alterado_em = models.DateTimeField("alterado em", auto_now=True)
    alterado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name="alterado por",
    )

    class Meta:
        ordering = ["nome"]
        verbose_name = "produto"
        verbose_name_plural = "produtos"

    def __str__(self):
        return f"{self.codigo} · {self.nome}"

    def get_absolute_url(self):
        return reverse("catalogo:detalhe_produto", args=[self.pk])
