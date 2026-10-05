from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .perfis import PERFIS_OPERADOR, possui_algum_perfil


class PerfilRequeridoMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restringe a view aos perfis em `perfis_permitidos` (padrão: Operador)."""

    perfis_permitidos = PERFIS_OPERADOR

    def test_func(self):
        return possui_algum_perfil(self.request.user, self.perfis_permitidos)
