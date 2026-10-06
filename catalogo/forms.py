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
                "saldo_estoque",
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
            "saldo_estoque",
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["saldo_estoque"].required = False

    def clean(self):
        dados = super().clean()
        # Itens sem controle de estoque (preparados na hora) não têm saldo.
        if not dados.get("controla_estoque"):
            dados["saldo_estoque"] = 0
        elif dados.get("saldo_estoque") is None:
            dados["saldo_estoque"] = 0
        return dados


class FormularioPesquisaProduto(forms.Form):
    termo = forms.CharField(label="Pesquisar", required=False, max_length=120)
    por = forms.ChoiceField(
        label="Pesquisar por", choices=PesquisarPor.choices, required=False, initial=PesquisarPor.NOME
    )
    categoria = forms.ChoiceField(
        label="Categoria", choices=[("", "Todas")] + Produto.Categoria.choices, required=False
    )
    incluir_inativos = forms.BooleanField(label="Incluir inativos", required=False)
