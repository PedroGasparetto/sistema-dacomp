from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


class Produto(models.Model):
    """Produto ou serviço oferecido pela lojinha (seção C.3 do relatório).

    A maior parte do catálogo é de bar e café: bebidas, lanches e doces.
    O saldo em estoque é informado no cadastro e baixado automaticamente
    quando uma venda é concluída.
    """

    class Categoria(models.TextChoices):
        CAFE = "cafe", "Cafés e bebidas quentes"
        BEBIDA = "bebida", "Bebidas"
        LANCHE = "lanche", "Lanches e salgados"
        DOCE = "doce", "Doces"
        OUTRO = "outro", "Outros"

    class Unidade(models.TextChoices):
        UNIDADE = "UN", "Unidade"
        COPO = "COPO", "Copo"
        FATIA = "FATIA", "Fatia"
        PACOTE = "PCT", "Pacote"
        CAIXA = "CX", "Caixa"
        DUZIA = "DZ", "Dúzia"
        QUILO = "KG", "Quilo"
        LITRO = "L", "Litro"

    # Identificação
    codigo = models.CharField("código interno", max_length=20, unique=True)
    nome = models.CharField("nome", max_length=120)
    categoria = models.CharField(
        "categoria", max_length=10, choices=Categoria.choices, default=Categoria.OUTRO
    )
    descricao = models.TextField("descrição", blank=True)
    marca = models.CharField("marca", max_length=60, blank=True)
    fornecedor = models.CharField(
        "fornecedor", max_length=120, blank=True, help_text="Nome de quem fornece o item, se houver."
    )

    codigo_barras = models.CharField(
        "código de barras",
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        help_text="Opcional; permite identificar o item com o leitor de código de barras.",
    )

    # Venda e estoque
    unidade = models.CharField(
        "unidade de venda", max_length=5, choices=Unidade.choices, default=Unidade.UNIDADE
    )
    preco_unitario = models.DecimalField(
        "preço de venda",
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    preco_custo = models.DecimalField(
        "preço de custo",
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Quanto a lojinha paga por unidade; usado para calcular o lucro.",
    )
    ativo = models.BooleanField("ativo", default=True)
    controla_estoque = models.BooleanField(
        "controla estoque",
        default=True,
        help_text="Desmarque para itens preparados na hora (como café coado) e para serviços.",
    )
    saldo_estoque = models.PositiveIntegerField(
        "quantidade em estoque",
        default=0,
        help_text="Quantidade disponível para venda; diminui automaticamente a cada venda concluída.",
    )

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

    @property
    def lucro_unitario(self):
        """Quanto sobra por unidade vendida; None sem preço de custo."""
        if self.preco_custo is None:
            return None
        return self.preco_unitario - self.preco_custo

    @property
    def margem_percentual(self):
        """Percentual de lucro sobre o preço de venda; None sem custo ou com venda a zero."""
        if self.lucro_unitario is None or not self.preco_unitario:
            return None
        return self.lucro_unitario / self.preco_unitario * 100
