from django.conf import settings
from django.contrib import messages
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, ListView, UpdateView

from .forms import FormularioCriacaoConta, FormularioEdicaoConta
from .mixins import PerfilRequeridoMixin
from .models import Usuario
from .perfis import PERFIS_GESTAO_CONTAS


class AlterarPropriaSenhaView(SuccessMessageMixin, PasswordChangeView):
    template_name = "contas/alterar_senha.html"
    success_url = reverse_lazy("nucleo:inicio")
    success_message = "Senha alterada com sucesso."


class ListaContasView(PerfilRequeridoMixin, ListView):
    perfis_permitidos = PERFIS_GESTAO_CONTAS
    template_name = "contas/lista_contas.html"
    context_object_name = "contas"
    paginate_by = settings.TAMANHO_PAGINA

    def get_queryset(self):
        return Usuario.objects.prefetch_related("groups").order_by("username")


class CriarContaView(PerfilRequeridoMixin, SuccessMessageMixin, CreateView):
    perfis_permitidos = PERFIS_GESTAO_CONTAS
    form_class = FormularioCriacaoConta
    template_name = "contas/formulario_conta.html"
    success_url = reverse_lazy("contas:lista_contas")
    success_message = "Conta de %(username)s criada."


class EditarContaView(PerfilRequeridoMixin, SuccessMessageMixin, UpdateView):
    perfis_permitidos = PERFIS_GESTAO_CONTAS
    model = Usuario
    form_class = FormularioEdicaoConta
    template_name = "contas/formulario_conta.html"
    context_object_name = "conta"
    success_url = reverse_lazy("contas:lista_contas")
    success_message = "Conta atualizada."

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "usuario_atuante": self.request.user}


class RedefinirSenhaContaView(PerfilRequeridoMixin, FormView):
    """Permite à Diretoria definir uma nova senha para um integrante."""

    perfis_permitidos = PERFIS_GESTAO_CONTAS
    form_class = SetPasswordForm
    template_name = "contas/redefinir_senha.html"

    def dispatch(self, request, *args, **kwargs):
        self.conta = get_object_or_404(Usuario, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.conta}

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "conta": self.conta}

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f"Senha de {self.conta.username} redefinida.")
        return redirect("contas:lista_contas")
