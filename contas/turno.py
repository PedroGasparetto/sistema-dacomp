"""Sessão por turno de atendimento (pedido do cliente na reunião de 17/11).

O login vale por um turno (DURACAO_TURNO_MINUTOS, padrão 1h40). Ao fim do turno a
sessão é encerrada e quem assume o caixa entra com a própria conta, para que
nenhuma venda fique registrada no nome de outra pessoa. A sessão também termina
quando o navegador é fechado (SESSION_EXPIRE_AT_BROWSER_CLOSE).
"""

from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.shortcuts import redirect, resolve_url
from django.utils import timezone
from django.utils.http import urlencode

CHAVE_INICIO_TURNO = "inicio_turno"


def duracao_turno():
    return timedelta(minutes=settings.DURACAO_TURNO_MINUTOS)


def fim_do_turno(request):
    """Momento em que a sessão atual expira, ou None sem login."""
    inicio = request.session.get(CHAVE_INICIO_TURNO)
    if inicio is None:
        return None
    return datetime.fromtimestamp(inicio, tz=timezone.get_current_timezone()) + duracao_turno()


@receiver(user_logged_in)
def registrar_inicio_do_turno(sender, request, user, **kwargs):
    if request is not None and hasattr(request, "session"):
        request.session[CHAVE_INICIO_TURNO] = timezone.now().timestamp()


class TurnoMiddleware:
    """Encerra a sessão de quem passou do tempo do turno e leva ao login."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if CHAVE_INICIO_TURNO not in request.session:
                # Sessões abertas antes desta versão começam o turno agora.
                request.session[CHAVE_INICIO_TURNO] = timezone.now().timestamp()
            elif timezone.now() >= fim_do_turno(request):
                logout(request)
                messages.info(request, "Seu turno terminou. Entre novamente para continuar.")
                url = resolve_url(settings.LOGIN_URL)
                if request.method == "GET":
                    url = f"{url}?{urlencode({'next': request.get_full_path()})}"
                return redirect(url)
        return self.get_response(request)
