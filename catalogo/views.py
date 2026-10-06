from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from contas.mixins import PerfilRequeridoMixin
from contas.perfis import PERFIS_GESTAO_PRODUTOS

from .forms import FormularioPesquisaProduto, FormularioProduto
from .models import Produto
from .servicos import PesquisarPor, pesquisar_produtos


class ListaProdutosView(PerfilRequeridoMixin, ListView):
    """UC05 – Consultar Produto."""

    template_name = "catalogo/lista_produtos.html"
    context_object_name = "produtos"
    paginate_by = settings.TAMANHO_PAGINA

    def get_queryset(self):
        self.formulario_pesquisa = FormularioPesquisaProduto(self.request.GET or None)
        if self.formulario_pesquisa.is_valid():
            dados = self.formulario_pesquisa.cleaned_data
            return pesquisar_produtos(
                dados["termo"],
                dados["por"] or PesquisarPor.NOME,
                dados["incluir_inativos"],
                dados["categoria"],
            )
        return pesquisar_produtos()

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["formulario_pesquisa"] = self.formulario_pesquisa
        contexto["pesquisou"] = any(
            self.request.GET.get(campo) for campo in ("termo", "categoria")
        )
        return contexto


class DetalheProdutoView(PerfilRequeridoMixin, DetailView):
    model = Produto
    template_name = "catalogo/detalhe_produto.html"
    context_object_name = "produto"


class CadastrarProdutoView(PerfilRequeridoMixin, SuccessMessageMixin, CreateView):
    """UC47 – Manter Cadastro de Produtos (inclusão)."""

    perfis_permitidos = PERFIS_GESTAO_PRODUTOS
    model = Produto
    form_class = FormularioProduto
    template_name = "catalogo/formulario_produto.html"
    success_message = "Produto %(nome)s cadastrado."

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        form.instance.alterado_por = self.request.user
        return super().form_valid(form)


class EditarProdutoView(PerfilRequeridoMixin, SuccessMessageMixin, UpdateView):
    """UC47 – Manter Cadastro de Produtos (alteração)."""

    perfis_permitidos = PERFIS_GESTAO_PRODUTOS
    model = Produto
    form_class = FormularioProduto
    template_name = "catalogo/formulario_produto.html"
    context_object_name = "produto"
    success_message = "Produto %(nome)s atualizado."

    def form_valid(self, form):
        # Grava só os campos do cadastro: o saldo pertence às movimentações de estoque.
        self.object = form.save(commit=False)
        self.object.alterado_por = self.request.user
        self.object.save(update_fields=[*form.Meta.fields, "alterado_por", "alterado_em"])
        messages.success(self.request, self.get_success_message(form.cleaned_data))
        return redirect(self.object)


class AlternarSituacaoProdutoView(PerfilRequeridoMixin, View):
    """UC47 – inativa ou reativa um item, preservando dados e histórico."""

    perfis_permitidos = PERFIS_GESTAO_PRODUTOS
    http_method_names = ["post"]

    def post(self, request, pk):
        produto = get_object_or_404(Produto, pk=pk)
        produto.ativo = not produto.ativo
        produto.alterado_por = request.user
        produto.save(update_fields=["ativo", "alterado_por", "alterado_em"])
        situacao = "reativado" if produto.ativo else "inativado"
        messages.success(request, f"Produto {produto.nome} {situacao}.")
        return redirect(produto)
