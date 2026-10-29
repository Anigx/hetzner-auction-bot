from hetzner_bot.delivery import build_embed, mention_prefix
from tests.factories import build_server

SERVER = build_server(id=3101875, price="39", nvme_gb=2000, hdd_gb=8000)


def field_text(embed, name):
    return next(f.value for f in embed.fields if f.name == name)


def test_embed_shows_key_specs():
    embed = build_embed(SERVER, None)
    assert "Ryzen 9 5950X" in embed.title
    assert "64 GB" in field_text(embed, "RAM")
    assert "FSN1-DC14" in field_text(embed, "Standort")
    assert "39" in field_text(embed, "Preis")


def test_embed_marks_price_drop():
    from decimal import Decimal

    embed = build_embed(SERVER, Decimal("45"))
    assert "45" in field_text(embed, "Preis")
    assert "39" in field_text(embed, "Preis")
    assert "3101875" in embed.footer.text


def test_embed_without_drop_has_no_old_price():
    embed = build_embed(SERVER, None)
    assert "45" not in field_text(embed, "Preis")


def test_mention_prefix_deduplicates():
    assert mention_prefix([3, 1, 3]) == "<@1> <@3>"
    assert mention_prefix([]) == ""


def test_embed_links_directly_to_the_server():
    embed = build_embed(SERVER, None)
    assert embed.url == "https://www.hetzner.com/sb/?freetext=3101875"
    assert "freetext=3101875" in field_text(embed, "Zum Server")


def test_embed_shows_gross_price_with_vat():
    embed = build_embed(SERVER, None, vat_rates=(19,))
    price = field_text(embed, "Preis")
    assert "39" in price          # netto
    assert "46,41 €" in price     # brutto
    assert "19 %" in price


def test_embed_can_show_two_tax_rates():
    price = field_text(build_embed(SERVER, None, vat_rates=(19, 20)), "Preis")
    assert "46,41 €" in price
    assert "46,80 €" in price
    assert "20 %" in price


def test_embed_can_lead_with_the_gross_price():
    price = field_text(build_embed(SERVER, None, vat_rates=(19,), gross_first=True), "Preis")
    assert price.startswith("**46,41 €/Monat brutto**")
    assert "netto: 39" in price


def test_embed_without_vat_has_no_gross_line():
    assert "brutto" not in field_text(build_embed(SERVER, None), "Preis")
