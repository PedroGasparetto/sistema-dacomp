from django.contrib import admin

from .forms import FormularioProduto
from .models import Produto


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    # Mesmas validações do cadastro pelo sistema (UC13), como não deixar de
    # controlar o estoque de um item com saldo.
    form = FormularioProduto
    list_display = ("codigo", "nome", "categoria", "unidade", "preco_unitario", "saldo_estoque", "ativo")
    list_filter = ("ativo", "categoria", "controla_estoque")
    search_fields = ("codigo", "nome", "codigo_barras", "marca", "fornecedor")
    readonly_fields = ("saldo_estoque", "criado_em", "criado_por", "alterado_em", "alterado_por")
    fields = (*FormularioProduto.Meta.fields, "ativo", *readonly_fields)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.criado_por = request.user
        obj.alterado_por = request.user
        super().save_model(request, obj, form, change)
