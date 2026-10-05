from django.contrib import admin

from .models import Produto


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome", "preco_unitario", "saldo_estoque", "controla_estoque", "ativo")
    list_filter = ("ativo", "controla_estoque")
    search_fields = ("codigo", "nome", "codigo_barras")
    readonly_fields = ("saldo_estoque", "criado_em", "criado_por", "alterado_em", "alterado_por")
