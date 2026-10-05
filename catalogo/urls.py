from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("", views.ListaProdutosView.as_view(), name="lista_produtos"),
    path("novo/", views.CadastrarProdutoView.as_view(), name="cadastrar_produto"),
    path("<int:pk>/", views.DetalheProdutoView.as_view(), name="detalhe_produto"),
    path("<int:pk>/editar/", views.EditarProdutoView.as_view(), name="editar_produto"),
    path("<int:pk>/situacao/", views.AlternarSituacaoProdutoView.as_view(), name="alternar_situacao"),
]
