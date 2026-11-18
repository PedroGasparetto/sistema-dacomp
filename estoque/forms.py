from django import forms

from catalogo.servicos import buscar_por_codigo

from .models import Movimentacao
from .servicos import validar_movimentacao

Tipo = Movimentacao.Tipo

CAMPO_DATA = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class FormularioMovimentacao(forms.Form):
    tipo = forms.ChoiceField(
        label="Tipo de transação",
        choices=[(Tipo.ENTRADA, Tipo.ENTRADA.label), (Tipo.AJUSTE, Tipo.AJUSTE.label)],
        widget=forms.RadioSelect,
    )
    produto = forms.CharField(
        label="Produto",
        max_length=50,
        help_text="Código interno ou código de barras (aceita leitor).",
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "off"}),
    )
    quantidade = forms.IntegerField(
        label="Quantidade",
        min_value=0,
        help_text="Entrada: quantidade recebida. Ajuste: saldo encontrado na contagem.",
    )
    motivo = forms.ChoiceField(
        label="Motivo do ajuste",
        choices=[("", "—")] + Movimentacao.MotivoAjuste.choices,
        required=False,
    )
    observacao = forms.CharField(label="Observação", max_length=255, required=False)

    def clean_produto(self):
        produto = buscar_por_codigo(self.cleaned_data["produto"])
        if produto is None:
            raise forms.ValidationError("Produto não encontrado.")
        return produto

    def clean(self):
        dados = super().clean()
        if self.errors:
            return dados
        try:
            validar_movimentacao(
                tipo=dados["tipo"],
                produto=dados["produto"],
                quantidade=dados["quantidade"],
                motivo=dados.get("motivo", ""),
            )
        except forms.ValidationError as erro:
            self.add_error(None, erro)
        return dados


class FormularioFiltroMovimentacoes(forms.Form):
    produto = forms.CharField(label="Produto", required=False, max_length=120)
    tipo = forms.ChoiceField(label="Tipo", choices=[("", "Todos")] + Tipo.choices, required=False)
    inicio = forms.DateField(label="De", required=False, widget=CAMPO_DATA)
    fim = forms.DateField(label="Até", required=False, widget=CAMPO_DATA)

    def clean(self):
        dados = super().clean()
        inicio, fim = dados.get("inicio"), dados.get("fim")
        if inicio and fim and inicio > fim:
            raise forms.ValidationError("A data inicial deve ser anterior ou igual à data final.")
        return dados
