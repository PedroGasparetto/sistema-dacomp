from django.urls import path

from . import views

app_name = "estoque"

urlpatterns = [
    path("movimentacoes/", views.ListaMovimentacoesView.as_view(), name="lista_movimentacoes"),
    path("movimentacoes/nova/", views.RegistrarMovimentacaoView.as_view(), name="registrar_movimentacao"),
    path("movimentacoes/<int:pk>/", views.DetalheMovimentacaoView.as_view(), name="detalhe_movimentacao"),
]
