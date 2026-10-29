import json
from decimal import Decimal
from pathlib import Path

from hetzner.client import parse_servers

FIXTURE = json.loads(Path("tests/fixtures/auction_snapshot.json").read_text("utf-8"))


def test_parse_returns_all_servers():
    servers = parse_servers(FIXTURE)
    assert len(servers) == len(FIXTURE["server"])
    assert len(servers) > 0


def test_parse_prices_are_exact_decimals():
    servers = {s.id: s for s in parse_servers(FIXTURE)}
    server = next(s for s in servers.values() if s.price_month_eur == Decimal("72"))
    assert str(server.price_month_eur) == "72"
    assert isinstance(server.price_hour_eur, Decimal)


def test_parse_extracts_storage_and_location():
    server = parse_servers(FIXTURE)[0]
    assert server.storage_total_gb > 0
    assert server.datacenter.startswith(("FSN", "NBG", "HEL"))


def test_parse_survives_missing_fields():
    payload = {"server": [{"Id": 1, "Hardware": {}, "Prices": {}, "Details": {}, "Timer": {}}]}
    servers = parse_servers(payload)
    assert servers[0].id == 1
    assert servers[0].price_month_eur == Decimal("0")
    assert servers[0].reduce_next_at is None
