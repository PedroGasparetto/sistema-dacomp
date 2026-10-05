from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def url_pagina(context, numero_pagina):
    """Monta o link de uma página preservando os filtros da consulta."""
    parametros = context["request"].GET.copy()
    parametros["page"] = numero_pagina
    return f"?{parametros.urlencode()}"
