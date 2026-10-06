from django import forms

from .models import Produto
from .servicos import PesquisarPor

DINHEIRO = forms.NumberInput(attrs={"step": "0.01", "inputmode": "decimal"})


class FormularioProduto(forms.ModelForm):
    GRUPOS = (
        ("Identificação", ("codigo", "nome", "categoria", "descricao", "marca", "fornecedor")),
        (
            "Venda e estoque",
            (
                "preco_unitario",
                "preco_custo",
                "unidade",
                "codigo_barras",
                "controla_estoque",
            ),
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
            "unidade",
            "codigo_barras",
            "controla_estoque",
        )
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "preco_unitario": DINHEIRO,
            "preco_custo": DINHEIRO,
            "codigo_barras": forms.TextInput(attrs={"autocomplete": "off"}),
        }

    def grupos(self):
        return [(titulo, [self[nome] for nome in nomes]) for titulo, nomes in self.GRUPOS]

    def clean_codigo(self):
        return self.cleaned_data["codigo"].strip().upper()

    def clean_codigo_barras(self):
        codigo_barras = (self.cleaned_data.get("codigo_barras") or "").strip()
        return codigo_barras or None

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
