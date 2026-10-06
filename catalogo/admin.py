from django.contrib import admin

from .models import Produto


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome", "categoria", "preco_unitario", "saldo_estoque", "ncm", "ativo")
    list_filter = ("ativo", "categoria", "controla_estoque", "csosn")
    search_fields = ("codigo", "nome", "codigo_barras", "ncm", "marca", "fornecedor")
    readonly_fields = ("saldo_estoque", "criado_em", "criado_por", "alterado_em", "alterado_por")
