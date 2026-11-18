from django.apps import AppConfig


class ContasConfig(AppConfig):
    name = "contas"
    verbose_name = "Contas e perfis"

    def ready(self):
        from . import turno  # noqa: F401  (registra o sinal de início do turno)
