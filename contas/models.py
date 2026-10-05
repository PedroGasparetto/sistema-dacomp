from django.contrib.auth.models import AbstractUser

from .perfis import TODOS_PERFIS


class Usuario(AbstractUser):
    """Conta interna de um integrante da equipe do DACOMP."""

    class Meta:
        ordering = ["first_name", "username"]
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def nomes_perfis(self):
        grupos = {grupo.name for grupo in self.groups.all()}
        return [perfil for perfil in TODOS_PERFIS if perfil in grupos]
