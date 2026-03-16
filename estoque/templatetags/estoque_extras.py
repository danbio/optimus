from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def brl(value):
    """Formata valor como moeda brasileira: R$ 1.234,56"""
    try:
        v = Decimal(str(value))
        formatted = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted}"
    except Exception:
        return value


@register.filter
def pct(value):
    """Formata percentual com 2 casas: 6,50%"""
    try:
        v = Decimal(str(value))
        return f"{v:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return value
