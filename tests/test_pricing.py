from decimal import Decimal

from hetzner_bot.pricing import format_eur, with_vat


def test_no_vat_keeps_net_price():
    assert with_vat(Decimal("39"), 0) == Decimal("39")
    assert with_vat(Decimal("39"), None) == Decimal("39")


def test_german_vat_is_applied_and_rounded():
    assert with_vat(Decimal("39"), 19) == Decimal("46.41")
    assert with_vat(Decimal("73.7"), 19) == Decimal("87.70")


def test_austrian_and_swiss_rates():
    assert with_vat(Decimal("100"), 20) == Decimal("120.00")
    assert with_vat(Decimal("100"), 8.1) == Decimal("108.10")


def test_format_uses_german_comma():
    assert format_eur(Decimal("46.41")) == "46,41 €"
    assert format_eur(Decimal("39")) == "39,00 €"
