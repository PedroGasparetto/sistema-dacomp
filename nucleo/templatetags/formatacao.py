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
