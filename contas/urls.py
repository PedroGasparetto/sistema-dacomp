from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "contas"

urlpatterns = [
    path("entrar/", auth_views.LoginView.as_view(redirect_authenticated_user=True), name="entrar"),
    path("sair/", auth_views.LogoutView.as_view(), name="sair"),
    path("minha-senha/", views.AlterarPropriaSenhaView.as_view(), name="alterar_senha"),
    path("usuarios/", views.ListaContasView.as_view(), name="lista_contas"),
    path("usuarios/nova/", views.CriarContaView.as_view(), name="criar_conta"),
    path("usuarios/<int:pk>/editar/", views.EditarContaView.as_view(), name="editar_conta"),
    path("usuarios/<int:pk>/senha/", views.RedefinirSenhaContaView.as_view(), name="redefinir_senha"),
]
