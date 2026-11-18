import os
from functools import lru_cache

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


def _versao(caminho):
    arquivo = finders.find(caminho)
    return int(os.path.getmtime(arquivo)) if arquivo else None


# Na rede local (sem DEBUG) os arquivos só mudam com uma nova instalação, que
# reinicia o servidor: a data é lida uma vez por arquivo, não a cada página.
_versao_em_cache = lru_cache(maxsize=None)(_versao)


@register.simple_tag
def estatico(caminho):
    """URL de um arquivo estático com a data de modificação (?v=…).

    Quando o CSS ou uma imagem muda, a URL muda junto e o navegador baixa a
    versão nova em vez de usar a cópia antiga do cache.
    """
    versao = _versao(caminho) if settings.DEBUG else _versao_em_cache(caminho)
    url = static(caminho)
    return f"{url}?v={versao}" if versao is not None else url
