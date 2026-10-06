import os

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def estatico(caminho):
    """URL de um arquivo estático com a data de modificação (?v=…).

    Quando o CSS ou uma imagem muda, a URL muda junto e o navegador baixa a
    versão nova em vez de usar a cópia antiga do cache.
    """
    url = static(caminho)
    arquivo = finders.find(caminho)
    if arquivo:
        url = f"{url}?v={int(os.path.getmtime(arquivo))}"
    return url
