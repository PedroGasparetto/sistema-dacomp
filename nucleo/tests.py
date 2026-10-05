from decimal import Decimal

from nucleo.templatetags.formatacao import moeda


def test_moeda_usa_formato_brasileiro():
    assert moeda(Decimal("46")) == "R$ 46,00"
    assert moeda(Decimal("1234.5")) == "R$ 1.234,50"
    assert moeda(None) == "—"
