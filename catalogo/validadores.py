"""Normalização e validação dos códigos usados nos itens de nota fiscal (NF-e/NFC-e)."""

import re

from django.core.exceptions import ValidationError

TAMANHOS_GTIN = (8, 12, 13, 14)


def somente_digitos(valor):
    """Remove pontos, traços e espaços: "2202.10.00" → "22021000"."""
    return re.sub(r"\D", "", valor or "")


def gtin_valido(codigo):
    """Confere o dígito verificador de um GTIN/EAN (8, 12, 13 ou 14 dígitos)."""
    if not codigo.isdigit() or len(codigo) not in TAMANHOS_GTIN:
        return False
    corpo, digito = codigo[:-1], int(codigo[-1])
    soma = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(corpo)))
    return (10 - soma % 10) % 10 == digito


def validar_gtin(codigo):
    if not gtin_valido(codigo):
        raise ValidationError(
            "Código de barras inválido: confira os dígitos (GTIN/EAN de 8, 12, 13 ou 14 dígitos)."
        )


def validar_digitos(valor, quantidade, nome):
    if len(valor) != quantidade:
        raise ValidationError(f"O {nome} deve ter {quantidade} dígitos.")
