from django import forms
from django.core.validators import MaxLengthValidator

from .models import Produto
from .servicos import PesquisarPor
from .validadores import somente_digitos, validar_digitos, validar_gtin

DINHEIRO = forms.NumberInput(attrs={"step": "0.01", "inputmode": "decimal"})


class FormularioProduto(forms.ModelForm):
    GRUPOS = (
        ("Identificação", ("codigo", "nome", "categoria", "descricao", "marca", "fornecedor")),
        ("Preço e estoque", ("preco_unitario", "preco_custo", "controla_estoque", "estoque_minimo")),
        (
            "Dados fiscais (nota fiscal)",
            ("codigo_barras", "ncm", "cest", "cfop", "unidade_comercial", "origem", "csosn"),
        ),
    )

    class Meta:
        model = Produto
        fields = (
            "codigo",
            "nome",
            "categoria",
            "descricao",
            "marca",
            "fornecedor",
            "preco_unitario",
            "preco_custo",
            "controla_estoque",
            "estoque_minimo",
            "codigo_barras",
            "ncm",
            "cest",
            "cfop",
            "unidade_comercial",
            "origem",
            "csosn",
        )
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "preco_unitario": DINHEIRO,
            "preco_custo": DINHEIRO,
            "codigo_barras": forms.TextInput(attrs={"inputmode": "numeric"}),
            "ncm": forms.TextInput(attrs={"inputmode": "numeric", "placeholder": "0000.00.00"}),
            "cest": forms.TextInput(attrs={"inputmode": "numeric", "placeholder": "00.000.00"}),
            "cfop": forms.TextInput(attrs={"inputmode": "numeric"}),
        }

    # Aceita os códigos fiscais com pontuação ("2202.10.00"); o tamanho real é
    # conferido depois que a pontuação é removida.
    TAMANHO_COM_PONTUACAO = {"codigo_barras": 20, "ncm": 10, "cest": 9}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome, limite in self.TAMANHO_COM_PONTUACAO.items():
            campo = self.fields[nome]
            campo.max_length = limite
            campo.validators = [v for v in campo.validators if not isinstance(v, MaxLengthValidator)]
            campo.widget.attrs["maxlength"] = str(limite)
        self.fields["estoque_minimo"].required = False

    def grupos(self):
        return [(titulo, [self[nome] for nome in nomes]) for titulo, nomes in self.GRUPOS]

    def clean_estoque_minimo(self):
        return self.cleaned_data.get("estoque_minimo") or 0

    def clean_codigo(self):
        return self.cleaned_data["codigo"].strip().upper()

    def clean_codigo_barras(self):
        codigo_barras = somente_digitos(self.cleaned_data.get("codigo_barras"))
        if codigo_barras:
            validar_gtin(codigo_barras)
        return codigo_barras or None

    def clean_ncm(self):
        ncm = somente_digitos(self.cleaned_data.get("ncm"))
        if ncm:
            validar_digitos(ncm, 8, "NCM")
        return ncm

    def clean_cest(self):
        cest = somente_digitos(self.cleaned_data.get("cest"))
        if cest:
            validar_digitos(cest, 7, "CEST")
        return cest

    def clean_cfop(self):
        cfop = somente_digitos(self.cleaned_data.get("cfop"))
        validar_digitos(cfop, 4, "CFOP")
        if cfop[0] not in "567":
            raise forms.ValidationError("Use um CFOP de saída (começando com 5, 6 ou 7).")
        return cfop

    def clean_controla_estoque(self):
        controla_estoque = self.cleaned_data["controla_estoque"]
        if self.instance.pk and not controla_estoque and self.instance.saldo_estoque > 0:
            raise forms.ValidationError(
                "Zere o saldo com um ajuste de estoque antes de deixar de controlar o estoque."
            )
        return controla_estoque


class FormularioPesquisaProduto(forms.Form):
    termo = forms.CharField(label="Pesquisar", required=False, max_length=120)
    por = forms.ChoiceField(
        label="Pesquisar por", choices=PesquisarPor.choices, required=False, initial=PesquisarPor.NOME
    )
    categoria = forms.ChoiceField(
        label="Categoria", choices=[("", "Todas")] + Produto.Categoria.choices, required=False
    )
    incluir_inativos = forms.BooleanField(label="Incluir inativos", required=False)
    para_repor = forms.BooleanField(label="Só itens para repor", required=False)
