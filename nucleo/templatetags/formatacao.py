from decimal import Decimal

from django import template
from django.utils.formats import number_format

register = template.Library()


@register.filter
def moeda(valor):
    """Formata um valor em reais: 1234.5 → "R$ 1.234,50"."""
    if valor is None or valor == "":
        return "—"
    return f"R$ {number_format(Decimal(valor), decimal_pos=2, use_l10n=True, force_grouping=True)}"


@register.filter
def ncm(valor):
    """22021000 → "2202.10.00"."""
    return f"{valor[:4]}.{valor[4:6]}.{valor[6:]}" if valor and len(valor) == 8 else valor


@register.filter
def cest(valor):
    """0300700 → "03.007.00"."""
    return f"{valor[:2]}.{valor[2:5]}.{valor[5:]}" if valor and len(valor) == 7 else valor
