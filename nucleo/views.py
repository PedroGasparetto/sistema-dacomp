from django.views.generic import TemplateView

from catalogo.models import Produto
from contas.mixins import PerfilRequeridoMixin
from vendas.models import Venda
from vendas.servicos import obter_caixa_aberto, resumir_caixa


class InicioView(PerfilRequeridoMixin, TemplateView):
    template_name = "nucleo/inicio.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["caixa"] = caixa = obter_caixa_aberto()
        contexto["resumo_caixa"] = resumir_caixa(caixa) if caixa else None
        contexto["produtos_ativos"] = Produto.objects.filter(ativo=True).count()
        contexto["ultimas_vendas"] = Venda.objects.filter(
            situacao=Venda.Situacao.CONCLUIDA
        ).select_related("operador")[:5]
        return contexto
