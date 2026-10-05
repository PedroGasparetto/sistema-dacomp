from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse

from catalogo.models import Produto

ZERO = Decimal("0.00")


class Caixa(models.Model):
    """Período de atendimento da lojinha (UC01 – Abrir Caixa, UC02 – Fechar Caixa)."""

    class Situacao(models.TextChoices):
        ABERTO = "aberto", "Aberto"
        FECHADO = "fechado", "Fechado"

    situacao = models.CharField("situação", max_length=10, choices=Situacao.choices, default=Situacao.ABERTO)
    valor_inicial = models.DecimalField("valor inicial em dinheiro", max_digits=10, decimal_places=2)
    aberto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+", verbose_name="aberto por"
    )
    aberto_em = models.DateTimeField("aberto em", auto_now_add=True)
    fechado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        verbose_name="fechado por",
    )
    fechado_em = models.DateTimeField("fechado em", null=True, blank=True)
    valor_esperado = models.DecimalField(
        "valor esperado em dinheiro", max_digits=10, decimal_places=2, null=True, blank=True
    )
    valor_contado = models.DecimalField(
        "valor contado em dinheiro", max_digits=10, decimal_places=2, null=True, blank=True
    )
    justificativa = models.CharField("justificativa da diferença", max_length=255, blank=True)

    class Meta:
        ordering = ["-aberto_em"]
        verbose_name = "caixa"
        verbose_name_plural = "caixas"
        constraints = [
            models.UniqueConstraint(
                fields=["situacao"], condition=Q(situacao="aberto"), name="apenas_um_caixa_aberto"
            )
        ]

    def __str__(self):
        return f"Caixa nº {self.pk}"

    @property
    def diferenca(self):
        if self.valor_contado is None or self.valor_esperado is None:
            return None
        return self.valor_contado - self.valor_esperado


class Venda(models.Model):
    """UC03 – Registrar Venda."""

    class Situacao(models.TextChoices):
        EM_ANDAMENTO = "andamento", "Em andamento"
        CONCLUIDA = "concluida", "Concluída"
        CANCELADA = "cancelada", "Cancelada"

    class FormaPagamento(models.TextChoices):
        DINHEIRO = "dinheiro", "Dinheiro"
        PIX = "pix", "PIX"
        CREDITO = "credito", "Cartão de crédito"
        DEBITO = "debito", "Cartão de débito"

    caixa = models.ForeignKey(Caixa, on_delete=models.PROTECT, related_name="vendas", verbose_name="caixa")
    operador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+", verbose_name="operador"
    )
    situacao = models.CharField(
        "situação", max_length=10, choices=Situacao.choices, default=Situacao.EM_ANDAMENTO
    )
    iniciada_em = models.DateTimeField("iniciada em", auto_now_add=True)
    concluida_em = models.DateTimeField("concluída em", null=True, blank=True)
    total = models.DecimalField("total", max_digits=10, decimal_places=2, default=ZERO)
    forma_pagamento = models.CharField(
        "forma de pagamento", max_length=10, choices=FormaPagamento.choices, blank=True
    )
    valor_recebido = models.DecimalField(
        "valor recebido", max_digits=10, decimal_places=2, null=True, blank=True
    )
    troco = models.DecimalField("troco", max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["-iniciada_em", "-id"]
        verbose_name = "venda"
        verbose_name_plural = "vendas"

    def __str__(self):
        return f"Venda nº {self.pk}"

    def get_absolute_url(self):
        return reverse("vendas:detalhe_venda", args=[self.pk])

    @property
    def total_itens(self):
        """Total calculado a partir dos itens; `total` guarda o valor na conclusão."""
        return sum((item.subtotal for item in self.itens.all()), ZERO)


class ItemVenda(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name="itens", verbose_name="venda")
    produto = models.ForeignKey(
        Produto, on_delete=models.PROTECT, related_name="itens_venda", verbose_name="produto"
    )
    quantidade = models.PositiveIntegerField("quantidade")
    # Preço praticado na venda: preservado mesmo que o cadastro mude depois.
    preco_unitario = models.DecimalField("preço unitário", max_digits=8, decimal_places=2)

    class Meta:
        ordering = ["id"]
        verbose_name = "item da venda"
        verbose_name_plural = "itens da venda"
        constraints = [
            models.UniqueConstraint(fields=["venda", "produto"], name="produto_unico_por_venda")
        ]

    def __str__(self):
        return f"{self.quantidade} × {self.produto.nome}"

    @property
    def subtotal(self):
        return self.preco_unitario * self.quantidade
