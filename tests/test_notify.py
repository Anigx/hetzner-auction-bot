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
