from django.conf import settings
from django.db import models
from django.urls import reverse

from catalogo.models import Produto


class Movimentacao(models.Model):
    """Registro imutável de uma alteração de saldo (RNF01 – rastreabilidade)."""

    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada de reposição"
        AJUSTE = "ajuste", "Ajuste de quantidade"
        VENDA = "venda", "Baixa por venda"

    class MotivoAjuste(models.TextChoices):
        PERDA = "perda", "Perda"
        VENCIMENTO = "vencimento", "Vencimento"
        AVARIA = "avaria", "Avaria"
        CORRECAO_CONTAGEM = "contagem", "Correção de contagem"
        OUTRO = "outro", "Outro"

    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name="movimentacoes",
        verbose_name="produto",
    )
    tipo = models.CharField("tipo", max_length=10, choices=Tipo.choices)
    quantidade_anterior = models.PositiveIntegerField("quantidade anterior")
    variacao = models.IntegerField("variação")
    quantidade_resultante = models.PositiveIntegerField("quantidade resultante")
    motivo = models.CharField("motivo", max_length=12, choices=MotivoAjuste.choices, blank=True)
    observacao = models.CharField("observação", max_length=255, blank=True)
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name="responsável",
    )
    realizada_em = models.DateTimeField("data e hora", auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-realizada_em", "-id"]
        verbose_name = "movimentação de estoque"
        verbose_name_plural = "movimentações de estoque"

    def __str__(self):
        return f"{self.get_tipo_display()} · {self.produto.nome} ({self.variacao:+d})"

    def get_absolute_url(self):
        return reverse("estoque:detalhe_movimentacao", args=[self.pk])
