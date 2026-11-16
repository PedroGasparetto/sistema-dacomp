from django.contrib import admin

from .models import Movimentacao


@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    """Somente leitura: o histórico só é criado pelos serviços de estoque."""

    list_display = (
        "realizada_em", "produto", "tipo", "quantidade_anterior", "variacao", "quantidade_resultante", "responsavel"
    )
    list_filter = ("tipo",)
    search_fields = ("produto__codigo", "produto__nome")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
