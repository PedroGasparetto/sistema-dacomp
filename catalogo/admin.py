from django.contrib import admin

from .models import Produto


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome", "categoria", "unidade", "preco_unitario", "saldo_estoque", "ativo")
    list_filter = ("ativo", "categoria", "controla_estoque")
    search_fields = ("codigo", "nome", "codigo_barras", "marca", "fornecedor")
    readonly_fields = ("saldo_estoque", "criado_em", "criado_por", "alterado_em", "alterado_por")
