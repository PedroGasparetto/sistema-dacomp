from decimal import Decimal

from django import forms

from contas.models import Usuario

from .models import Venda

CAMPO_DATA = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


def _campo_dinheiro(label, **kwargs):
    return forms.DecimalField(
        label=label,
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.00"),
        widget=forms.NumberInput(attrs={"step": "0.01", "inputmode": "decimal"}),
        **kwargs,
    )


class FormularioAbrirCaixa(forms.Form):
    valor_inicial = _campo_dinheiro(
        "Valor inicial em dinheiro (R$)", help_text="Troco disponível na gaveta no início do atendimento."
    )


class FormularioFecharCaixa(forms.Form):
    valor_contado = _campo_dinheiro("Valor contado em dinheiro (R$)")
    justificativa = forms.CharField(
        label="Justificativa da diferença",
        max_length=255,
        required=False,
        help_text="Obrigatória quando o valor contado for diferente do esperado.",
    )


class FormularioAdicionarItem(forms.Form):
    termo = forms.CharField(label="Produto", max_length=120)
    quantidade = forms.IntegerField(label="Qtd.", min_value=1, initial=1)


class FormularioQuantidade(forms.Form):
    quantidade = forms.IntegerField(label="Quantidade", min_value=1)


class FormularioPagamento(forms.Form):
    forma_pagamento = forms.ChoiceField(
        label="Forma de pagamento",
        choices=Venda.FormaPagamento.choices,
        widget=forms.RadioSelect,
        initial=Venda.FormaPagamento.DINHEIRO,
    )
    valor_recebido = _campo_dinheiro("Quantia recebida (R$)", required=False)


class FormularioFiltroVendas(forms.Form):
    identificador = forms.IntegerField(label="Nº da venda", required=False, min_value=1)
    situacao = forms.ChoiceField(
        label="Situação", choices=[("", "Todas")] + Venda.Situacao.choices, required=False
    )
    operador = forms.ModelChoiceField(
        label="Operador", queryset=Usuario.objects.order_by("first_name", "username"), required=False, empty_label="Todos"
    )
    caixa = forms.IntegerField(label="Nº do caixa", required=False, min_value=1)
    inicio = forms.DateField(label="De", required=False, widget=CAMPO_DATA)
    fim = forms.DateField(label="Até", required=False, widget=CAMPO_DATA)

    def clean(self):
        dados = super().clean()
        inicio, fim = dados.get("inicio"), dados.get("fim")
        if inicio and fim and inicio > fim:
            raise forms.ValidationError("A data inicial deve ser anterior ou igual à data final.")
        return dados


class FormularioDevolucao(forms.Form):
    """UC16 – quantidade a devolver de cada item ainda devolvível e o motivo."""

    motivo = forms.CharField(
        label="Motivo da devolução",
        max_length=255,
        help_text="Por exemplo: produto com defeito, troca de sabor, cobrança em dobro.",
    )

    def __init__(self, *args, itens, **kwargs):
        super().__init__(*args, **kwargs)
        self.itens = itens
        for item in itens:
            self.fields[self._nome(item)] = forms.IntegerField(
                label=item.produto.nome,
                min_value=0,
                max_value=item.quantidade_devolvivel,
                initial=0,
                required=False,
            )
        self.order_fields([*(self._nome(item) for item in itens), "motivo"])

    @staticmethod
    def _nome(item):
        return f"item_{item.pk}"

    def linhas(self):
        return [(item, self[self._nome(item)]) for item in self.itens]

    def quantidades(self):
        return {item.pk: self.cleaned_data.get(self._nome(item)) or 0 for item in self.itens}

    def clean(self):
        dados = super().clean()
        if not self.errors and not any(self.quantidades().values()):
            raise forms.ValidationError("Informe a quantidade de pelo menos um item a devolver.")
        return dados
