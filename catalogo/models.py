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

    class Unidade(models.TextChoices):
        UNIDADE = "UN", "UN – unidade"
        PACOTE = "PCT", "PCT – pacote"
        CAIXA = "CX", "CX – caixa"
        DUZIA = "DZ", "DZ – dúzia"
        QUILO = "KG", "KG – quilograma"
        GRAMA = "G", "G – grama"
        LITRO = "L", "L – litro"
        MILILITRO = "ML", "ML – mililitro"

    class Origem(models.TextChoices):
        """Origem da mercadoria (tabela da NF-e)."""

        NACIONAL = "0", "0 – Nacional"
        ESTRANGEIRA_IMPORTACAO_DIRETA = "1", "1 – Estrangeira, importação direta"
        ESTRANGEIRA_MERCADO_INTERNO = "2", "2 – Estrangeira, adquirida no mercado interno"
        NACIONAL_IMPORTACAO_40_70 = "3", "3 – Nacional, conteúdo de importação entre 40% e 70%"
        NACIONAL_PROCESSO_BASICO = "4", "4 – Nacional, processos produtivos básicos"
        NACIONAL_IMPORTACAO_ATE_40 = "5", "5 – Nacional, conteúdo de importação até 40%"
        ESTRANGEIRA_DIRETA_SEM_SIMILAR = "6", "6 – Estrangeira, importação direta sem similar nacional"
        ESTRANGEIRA_INTERNO_SEM_SIMILAR = "7", "7 – Estrangeira, mercado interno sem similar nacional"
        NACIONAL_IMPORTACAO_ACIMA_70 = "8", "8 – Nacional, conteúdo de importação acima de 70%"

    class Csosn(models.TextChoices):
        """Situação tributária do ICMS para o Simples Nacional (CSOSN)."""

        TRIBUTADA_SEM_CREDITO = "102", "102 – Tributada sem permissão de crédito"
        ISENCAO_FAIXA_RECEITA = "103", "103 – Isenção para faixa de receita bruta"
        IMUNE = "300", "300 – Imune"
        NAO_TRIBUTADA = "400", "400 – Não tributada"
        SUBSTITUICAO_TRIBUTARIA = "500", "500 – ICMS cobrado anteriormente por substituição tributária"
        OUTROS = "900", "900 – Outros"

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

    # Preço e estoque
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
        help_text="Quanto a lojinha paga por unidade; usado para calcular a margem.",
    )
    ativo = models.BooleanField("ativo", default=True)
    controla_estoque = models.BooleanField(
        "controla estoque",
        default=True,
        help_text="Desmarque para itens preparados na hora (como café coado) e para serviços.",
    )
    estoque_minimo = models.PositiveIntegerField(
        "estoque mínimo", default=0, help_text="Abaixo desta quantidade o item é sinalizado para reposição."
    )
    saldo_estoque = models.PositiveIntegerField("saldo em estoque", default=0, editable=False)

    # Dados fiscais (item da NF-e/NFC-e)
    codigo_barras = models.CharField(
        "código de barras (GTIN/EAN)",
        max_length=14,
        unique=True,
        null=True,
        blank=True,
        help_text="Deixe em branco se o item não tiver código de barras (na nota: SEM GTIN).",
    )
    ncm = models.CharField(
        "NCM", max_length=8, blank=True, help_text="Nomenclatura Comum do Mercosul, 8 dígitos."
    )
    cest = models.CharField(
        "CEST",
        max_length=7,
        blank=True,
        help_text="Código Especificador da Substituição Tributária, 7 dígitos (itens com ST).",
    )
    cfop = models.CharField(
        "CFOP de venda",
        max_length=4,
        default="5102",
        help_text="5102: revenda de mercadoria; 5405: revenda com substituição tributária.",
    )
    unidade_comercial = models.CharField(
        "unidade comercial", max_length=3, choices=Unidade.choices, default=Unidade.UNIDADE
    )
    origem = models.CharField(
        "origem da mercadoria", max_length=1, choices=Origem.choices, default=Origem.NACIONAL
    )
    csosn = models.CharField(
        "CSOSN (ICMS)", max_length=3, choices=Csosn.choices, default=Csosn.TRIBUTADA_SEM_CREDITO
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
    def abaixo_do_minimo(self):
        return self.controla_estoque and self.estoque_minimo > 0 and self.saldo_estoque < self.estoque_minimo

    @property
    def margem_percentual(self):
        """Margem sobre o preço de venda; None sem preço de custo ou com venda a zero."""
        if self.preco_custo is None or not self.preco_unitario:
            return None
        return (self.preco_unitario - self.preco_custo) / self.preco_unitario * 100

    @property
    def gtin_nota(self):
        """Valor do campo GTIN na nota fiscal."""
        return self.codigo_barras or "SEM GTIN"
