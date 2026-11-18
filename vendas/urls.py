from django.urls import path

from . import views

app_name = "vendas"

urlpatterns = [
    path("pdv/", views.PdvView.as_view(), name="pdv"),
    path("pdv/itens/adicionar/", views.AdicionarItemView.as_view(), name="adicionar_item"),
    path("pdv/itens/<int:pk>/quantidade/", views.AlterarQuantidadeView.as_view(), name="alterar_quantidade"),
    path("pdv/itens/<int:pk>/remover/", views.RemoverItemView.as_view(), name="remover_item"),
    path("pdv/<int:pk>/cancelar/", views.CancelarVendaView.as_view(), name="cancelar_venda"),
    path("pdv/<int:pk>/pagamento/", views.PagamentoView.as_view(), name="pagamento"),
    path("caixa/abrir/", views.AbrirCaixaView.as_view(), name="abrir_caixa"),
    path("caixa/fechar/", views.FecharCaixaView.as_view(), name="fechar_caixa"),
    path("caixa/<int:pk>/", views.DetalheCaixaView.as_view(), name="detalhe_caixa"),
    path("", views.ListaVendasView.as_view(), name="lista_vendas"),
    path("relatorio/", views.RelatorioVendasView.as_view(), name="relatorio_vendas"),
    path("<int:pk>/", views.DetalheVendaView.as_view(), name="detalhe_venda"),
    path("<int:pk>/devolucao/", views.RegistrarDevolucaoView.as_view(), name="registrar_devolucao"),
]
