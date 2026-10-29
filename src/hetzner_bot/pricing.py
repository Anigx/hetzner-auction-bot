"""Preise: netto aus der Quelle, brutto je nach Steuersatz."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def with_vat(net: Decimal, vat_percent: float | int | None = 0) -> Decimal:
    """Rechnet netto auf brutto um. Ohne Steuersatz bleibt der Nettopreis stehen."""
    if not vat_percent or vat_percent <= 0:
        return net
    try:
        factor = Decimal(1) + Decimal(str(vat_percent)) / Decimal(100)
    except InvalidOperation:
        return net
    return (net * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def format_eur(amount: Decimal) -> str:
    """Deutsche Schreibweise mit Komma, ohne Tausenderpunkt-Sonderfaelle."""
    return f"{amount:.2f}".replace(".", ",") + " €"
