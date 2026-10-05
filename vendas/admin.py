from django.contrib import admin

from .models import Caixa, ItemVenda, Venda


class ItemVendaInline(admin.TabularInline):
    model = ItemVenda
    extra = 0
    readonly_fields = ("produto", "quantidade", "preco_unitario")
    can_delete = False


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    """Somente leitura: vendas são registradas pelo PDV."""

    list_display = ("id", "iniciada_em", "operador", "caixa", "situacao", "forma_pagamento", "total")
    list_filter = ("situacao", "forma_pagamento")
    inlines = [ItemVendaInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Caixa)
class CaixaAdmin(admin.ModelAdmin):
    list_display = ("id", "situacao", "aberto_em", "aberto_por", "fechado_em", "valor_esperado", "valor_contado")
    list_filter = ("situacao",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
