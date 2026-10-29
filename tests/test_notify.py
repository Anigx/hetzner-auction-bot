from decimal import Decimal

from hetzner.models import Server
from notify import build_embed, mention_prefix

SERVER = Server(
    id=3101875,
    cpu_name="AMD Ryzen 9 5950X",
    sockets=1,
    ram_gb=64,
    ecc=True,
    storage_total_gb=4096,
    nvme_gb=2000,
    sata_gb=0,
    hdd_gb=8000,
    location="FSN",
    datacenter="FSN1-DC14",
    bandwidth_mbit=1000,
    traffic="unlimited",
    price_month_eur=Decimal("39"),
    price_hour_eur=Decimal("0.05"),
    setup_eur=Decimal("0"),
    extra_ips=1,
    reduce_next_at=None,
)


def field_text(embed, name):
    return next(f.value for f in embed.fields if f.name == name)


def test_embed_shows_key_specs():
    embed = build_embed(SERVER, None)
    assert "Ryzen 9 5950X" in embed.title
    assert "64 GB" in field_text(embed, "RAM")
    assert "FSN1-DC14" in field_text(embed, "Standort")
    assert "39" in field_text(embed, "Preis")


def test_embed_marks_price_drop():
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
