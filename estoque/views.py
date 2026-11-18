from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView, ListView

from contas.mixins import PerfilRequeridoMixin

from .forms import FormularioFiltroMovimentacoes, FormularioMovimentacao
from .models import Movimentacao
from .servicos import (
    calcular_novo_saldo,
    filtrar_movimentacoes,
    gerar_relatorio_movimentacoes,
    registrar_movimentacao,
)


class RegistrarMovimentacaoView(PerfilRequeridoMixin, FormView):
    """UC10 – Realizar Transação no Estoque.

    Segue o fluxo essencial: o operador informa os dados, o sistema apresenta
    o resumo (quantidade anterior, variação e resultante) e só registra após
    a confirmação.
    """

    form_class = FormularioMovimentacao
    template_name = "estoque/formulario_movimentacao.html"

    def get_initial(self):
        return {
            "produto": self.request.GET.get("produto", ""),
            "tipo": self.request.GET.get("tipo", Movimentacao.Tipo.ENTRADA),
        }

    def form_valid(self, form):
        if "corrigir" in self.request.POST:
            return self.render_to_response(self.get_context_data(form=form))
        if "confirmar" not in self.request.POST:
            return self._apresentar_resumo(form)

        dados = form.cleaned_data
        try:
            movimentacao = registrar_movimentacao(
                tipo=dados["tipo"],
                produto=dados["produto"],
                quantidade=dados["quantidade"],
                motivo=dados["motivo"],
                observacao=dados["observacao"],
                usuario=self.request.user,
            )
        except ValidationError as erro:
            form.add_error(None, erro)
            return self.form_invalid(form)

        messages.success(self.request, "Transação registrada e saldo atualizado.")
        return redirect(movimentacao)

    def _apresentar_resumo(self, form):
        dados = form.cleaned_data
        produto = dados["produto"]
        quantidade_resultante = calcular_novo_saldo(dados["tipo"], produto.saldo_estoque, dados["quantidade"])
        return render(
            self.request,
            "estoque/confirmar_movimentacao.html",
            {
                "form": form,
                "produto": produto,
                "descricao_tipo": Movimentacao.Tipo(dados["tipo"]).label,
                "descricao_motivo": dict(Movimentacao.MotivoAjuste.choices).get(dados["motivo"], ""),
                "quantidade_anterior": produto.saldo_estoque,
                "quantidade_resultante": quantidade_resultante,
                "variacao": quantidade_resultante - produto.saldo_estoque,
            },
        )


class ListaMovimentacoesView(PerfilRequeridoMixin, ListView):
    """UC09 – Consultar Movimentação no Estoque (ponto de extensão Gerar relatório)."""

    template_name = "estoque/lista_movimentacoes.html"
    context_object_name = "movimentacoes"
    paginate_by = settings.TAMANHO_PAGINA

    def get_queryset(self):
        self.formulario_filtro = FormularioFiltroMovimentacoes(self.request.GET or None)
        if self.formulario_filtro.is_bound and not self.formulario_filtro.is_valid():
            return Movimentacao.objects.none()
        dados = self.formulario_filtro.cleaned_data if self.formulario_filtro.is_bound else {}
        return filtrar_movimentacoes(
            termo_produto=dados.get("produto", ""),
            tipo=dados.get("tipo", ""),
            inicio=dados.get("inicio"),
            fim=dados.get("fim"),
        )

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "formulario_filtro": self.formulario_filtro}


class DetalheMovimentacaoView(PerfilRequeridoMixin, DetailView):
    template_name = "estoque/detalhe_movimentacao.html"
    context_object_name = "movimentacao"
    queryset = Movimentacao.objects.select_related("produto", "responsavel")


class RelatorioMovimentacoesView(PerfilRequeridoMixin, View):
    """UC14 – Gerar Relatórios Básicos: relatório das movimentações filtradas no UC09."""

    def get(self, request):
        formulario = FormularioFiltroMovimentacoes(request.GET or None)
        if formulario.is_bound and not formulario.is_valid():
            messages.error(request, "Corrija os filtros da consulta antes de gerar o relatório.")
            return redirect(f"{reverse('estoque:lista_movimentacoes')}?{request.GET.urlencode()}")
        dados = formulario.cleaned_data if formulario.is_bound else {}
        relatorio = gerar_relatorio_movimentacoes(
            termo_produto=dados.get("produto", ""),
            tipo=dados.get("tipo", ""),
            inicio=dados.get("inicio"),
            fim=dados.get("fim"),
        )
        return render(
            request,
            "estoque/relatorio_movimentacoes.html",
            {
                "relatorio": relatorio,
                "filtros": dados,
                "descricao_tipo": dict(Movimentacao.Tipo.choices).get(dados.get("tipo"), ""),
                "consulta": request.GET.urlencode(),
            },
        )
