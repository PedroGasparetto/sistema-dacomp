from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from catalogo.models import Produto
from catalogo.servicos import pesquisar_produtos
from contas.mixins import PerfilRequeridoMixin

from .forms import (
    FormularioAbrirCaixa,
    FormularioAdicionarItem,
    FormularioFecharCaixa,
    FormularioFiltroVendas,
    FormularioPagamento,
    FormularioQuantidade,
)
from .models import ZERO, Caixa, ItemVenda, Venda
from .servicos import (
    abrir_caixa,
    adicionar_item,
    alterar_quantidade,
    cancelar_venda,
    concluir_venda,
    fechar_caixa,
    filtrar_vendas,
    iniciar_ou_retomar_venda,
    localizar_produtos_para_venda,
    obter_caixa_aberto,
    obter_venda_em_andamento,
    remover_item,
    resumir_caixa,
    verificar_finalizacao,
)


def _avisar_erros(request, erro):
    for mensagem in erro.messages:
        messages.error(request, mensagem)


# PDV (UC05 – Registrar Venda) ---------------------------------------------


CHAVE_CATEGORIA_PDV = "pdv_categoria"


def _renderizar_pdv(request, **extra):
    caixa = obter_caixa_aberto()
    venda = obter_venda_em_andamento(request.user, caixa)
    itens = list(venda.itens.all()) if venda else []
    categoria = request.session.get(CHAVE_CATEGORIA_PDV, "")
    contexto = {
        "caixa": caixa,
        "venda": venda,
        "itens": itens,
        "total": venda.total_itens if venda else ZERO,
        "quantidade_itens": sum(item.quantidade for item in itens),
        "formulario_item": FormularioAdicionarItem(),
        "candidatos": [],
        # Grade de atalhos: itens de bar e café costumam não ter código de barras.
        "categorias": Produto.Categoria.choices,
        "categoria_atual": categoria,
        "atalhos": pesquisar_produtos(categoria=categoria) if caixa else [],
        **extra,
    }
    return render(request, "vendas/pdv.html", contexto)


class PdvView(PerfilRequeridoMixin, View):
    def get(self, request):
        if "categoria" in request.GET:
            categoria = request.GET["categoria"]
            request.session[CHAVE_CATEGORIA_PDV] = categoria if categoria in Produto.Categoria.values else ""
        return _renderizar_pdv(request)


class AdicionarItemView(PerfilRequeridoMixin, View):
    http_method_names = ["post"]

    def post(self, request):
        formulario = FormularioAdicionarItem(request.POST)
        if not formulario.is_valid():
            messages.error(request, "Informe o produto e uma quantidade maior que zero.")
            return redirect("vendas:pdv")

        termo = formulario.cleaned_data["termo"]
        quantidade = formulario.cleaned_data["quantidade"]
        produtos = localizar_produtos_para_venda(termo)
        if not produtos:
            messages.error(request, f"Nenhum produto ativo encontrado para “{termo}”.")
            return redirect("vendas:pdv")
        if len(produtos) > 1:
            return _renderizar_pdv(request, candidatos=produtos, quantidade_candidatos=quantidade)

        try:
            # A venda só é criada se o primeiro item for aceito.
            with transaction.atomic():
                venda = iniciar_ou_retomar_venda(request.user)
                adicionar_item(venda=venda, produto=produtos[0], quantidade=quantidade)
        except ValidationError as erro:
            _avisar_erros(request, erro)
        return redirect("vendas:pdv")


def _item_da_venda_em_andamento(request, pk):
    return get_object_or_404(
        ItemVenda.objects.select_related("venda", "produto"),
        pk=pk,
        venda__operador=request.user,
        venda__situacao=Venda.Situacao.EM_ANDAMENTO,
    )


class AlterarQuantidadeView(PerfilRequeridoMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        item = _item_da_venda_em_andamento(request, pk)
        formulario = FormularioQuantidade(request.POST)
        if not formulario.is_valid():
            messages.error(request, "A quantidade deve ser maior que zero. Para tirar o item, use Remover.")
            return redirect("vendas:pdv")
        try:
            alterar_quantidade(item=item, quantidade=formulario.cleaned_data["quantidade"])
        except ValidationError as erro:
            _avisar_erros(request, erro)
        return redirect("vendas:pdv")


class RemoverItemView(PerfilRequeridoMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        remover_item(item=_item_da_venda_em_andamento(request, pk))
        return redirect("vendas:pdv")


def _venda_em_andamento(request, pk):
    return get_object_or_404(
        Venda.objects.select_related("caixa"),
        pk=pk,
        operador=request.user,
        situacao=Venda.Situacao.EM_ANDAMENTO,
    )


class CancelarVendaView(PerfilRequeridoMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        venda = cancelar_venda(venda=_venda_em_andamento(request, pk))
        messages.success(request, f"{venda} cancelada. Nenhum pagamento ou baixa de estoque foi registrado.")
        return redirect("vendas:pdv")


class PagamentoView(PerfilRequeridoMixin, View):
    """UC06 – Receber Pagamento, incluído na finalização do UC05."""

    template_name = "vendas/pagamento.html"

    def get(self, request, pk):
        venda = _venda_em_andamento(request, pk)
        try:
            verificar_finalizacao(venda)
        except ValidationError as erro:
            _avisar_erros(request, erro)
            return redirect("vendas:pdv")
        return self._renderizar(request, venda, FormularioPagamento())

    def post(self, request, pk):
        venda = _venda_em_andamento(request, pk)
        formulario = FormularioPagamento(request.POST)
        if formulario.is_valid():
            try:
                venda = concluir_venda(
                    venda=venda,
                    forma_pagamento=formulario.cleaned_data["forma_pagamento"],
                    valor_recebido=formulario.cleaned_data["valor_recebido"],
                )
            except ValidationError as erro:
                if hasattr(erro, "error_dict"):
                    formulario.add_error(None, erro)
                else:
                    _avisar_erros(request, erro)
                    return redirect("vendas:pdv")
            else:
                messages.success(request, f"{venda} concluída.")
                return redirect(f"{venda.get_absolute_url()}?pdv=1")
        return self._renderizar(request, venda, formulario)

    def _renderizar(self, request, venda, formulario):
        itens = list(venda.itens.select_related("produto"))
        return render(
            request,
            self.template_name,
            {"venda": venda, "itens": itens, "total": venda.total_itens, "formulario": formulario},
        )


# Caixa (UC03 e UC04) ---------------------------------------------------------


class AbrirCaixaView(PerfilRequeridoMixin, View):
    template_name = "vendas/abrir_caixa.html"

    def get(self, request):
        if obter_caixa_aberto():
            messages.info(request, "O caixa já está aberto.")
            return redirect("vendas:pdv")
        return render(request, self.template_name, {"formulario": FormularioAbrirCaixa()})

    def post(self, request):
        formulario = FormularioAbrirCaixa(request.POST)
        if formulario.is_valid():
            try:
                caixa = abrir_caixa(usuario=request.user, valor_inicial=formulario.cleaned_data["valor_inicial"])
            except ValidationError as erro:
                if hasattr(erro, "error_dict"):
                    formulario.add_error(None, erro)
                else:
                    _avisar_erros(request, erro)
                    return redirect("vendas:pdv")
            else:
                messages.success(request, f"{caixa} aberto. Bom atendimento!")
                return redirect("vendas:pdv")
        return render(request, self.template_name, {"formulario": formulario})


class FecharCaixaView(PerfilRequeridoMixin, View):
    template_name = "vendas/fechar_caixa.html"

    def get(self, request):
        caixa = obter_caixa_aberto()
        if caixa is None:
            messages.info(request, "Não há caixa aberto.")
            return redirect("vendas:pdv")
        return self._renderizar(request, caixa, FormularioFecharCaixa())

    def post(self, request):
        caixa = obter_caixa_aberto()
        if caixa is None:
            messages.info(request, "Não há caixa aberto.")
            return redirect("vendas:pdv")
        formulario = FormularioFecharCaixa(request.POST)
        if formulario.is_valid():
            try:
                caixa = fechar_caixa(
                    caixa=caixa,
                    usuario=request.user,
                    valor_contado=formulario.cleaned_data["valor_contado"],
                    justificativa=formulario.cleaned_data["justificativa"],
                )
            except ValidationError as erro:
                formulario.add_error(None, erro)
            else:
                messages.success(request, f"{caixa} fechado. Novas vendas ficam bloqueadas até a próxima abertura.")
                return redirect("vendas:detalhe_caixa", pk=caixa.pk)
        return self._renderizar(request, caixa, formulario)

    def _renderizar(self, request, caixa, formulario):
        # Inclusão do UC07: vendas concluídas do caixa atual.
        vendas = filtrar_vendas(caixa=caixa.pk, situacao=Venda.Situacao.CONCLUIDA)
        return render(
            request,
            self.template_name,
            {"caixa": caixa, "resumo": resumir_caixa(caixa), "vendas": vendas, "formulario": formulario},
        )


class DetalheCaixaView(PerfilRequeridoMixin, DetailView):
    model = Caixa
    template_name = "vendas/detalhe_caixa.html"
    context_object_name = "caixa"

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "resumo": resumir_caixa(self.object)}


# Consulta de vendas (UC07) ---------------------------------------------------


class ListaVendasView(PerfilRequeridoMixin, ListView):
    template_name = "vendas/lista_vendas.html"
    context_object_name = "vendas"
    paginate_by = settings.TAMANHO_PAGINA

    def get_queryset(self):
        self.formulario_filtro = FormularioFiltroVendas(self.request.GET or None)
        if self.formulario_filtro.is_bound and not self.formulario_filtro.is_valid():
            return Venda.objects.none()
        dados = self.formulario_filtro.cleaned_data if self.formulario_filtro.is_bound else {}
        return filtrar_vendas(**{campo: valor for campo, valor in dados.items() if valor})

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "formulario_filtro": self.formulario_filtro}


class DetalheVendaView(PerfilRequeridoMixin, DetailView):
    template_name = "vendas/detalhe_venda.html"
    context_object_name = "venda"
    queryset = Venda.objects.select_related("operador", "caixa").prefetch_related("itens__produto")
