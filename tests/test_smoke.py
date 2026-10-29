"""End-to-End über die echte Fixture: parsen, filtern, posten, deduplizieren.

Kein Netzwerk: der Snapshot ist die Datenquelle, Discord ist ein Fake.
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from hetzner_bot.auction import parse_servers
from hetzner_bot.domain import Criteria
from hetzner_bot.engine import Poller, matches
from hetzner_bot.storage import Store
from tests.factories import build_server

FIXTURE = json.loads(Path("tests/fixtures/auction_snapshot.json").read_text("utf-8"))
SERVERS = parse_servers(FIXTURE)


class FakeChannel:
    def __init__(self):
        self.sent = []

    async def send(self, content=None, embed=None):
        self.sent.append((content, embed))


class FakeBot:
    def __init__(self, channel):
        self.channel = channel

    def get_channel(self, cid):
        return self.channel


@pytest.fixture
def store(tmp_path):
    database = Store(tmp_path / "smoke.sqlite3")
    database.init_schema()
    yield database
    database.close()


def field_text(embed, name):
    return next(f.value for f in embed.fields if f.name == name)


@pytest.mark.asyncio
async def test_full_run_on_real_auction_data(store, make_filter):
    criteria = Criteria(max_price=Decimal("80"))
    expected = [server for server in SERVERS if matches(criteria, server)]
    assert expected, "Fixture enthaelt keinen Server unter 80 Euro"

    store.set_channel(1, 99)
    store.save_filter(1, 2, "standard", criteria, mention=True)
    channel = FakeChannel()
    poller = Poller(FakeBot(channel), store, fetch=lambda: SERVERS, max_posts=15)

    report = await poller.run_once()

    assert report.fetched == len(SERVERS)
    assert report.posted == 15
    assert len(channel.sent) == 15
    for content, embed in channel.sent:
        assert content.startswith("<@2>")
        assert embed is not None
        assert "€/Monat" in field_text(embed, "Preis")

    # Die Warteschlange wird ueber weitere Laeufe abgearbeitet: jeder Treffer
    # genau einmal, nie doppelt.
    runs = 1
    while report.queued:
        report = await poller.run_once()
        runs += 1
        assert runs < 30, "Warteschlange leert sich nicht"

    seen_ids = [embed.footer.text.rsplit(" ", 1)[-1] for _, embed in channel.sent]
    assert len(seen_ids) == len(set(seen_ids)), "ein Server wurde doppelt gepostet"
    assert len(seen_ids) == len(expected)

    # Danach ist Ruhe.
    final = await poller.run_once()
    assert final.posted == 0
    assert len(channel.sent) == len(expected)


@pytest.mark.asyncio
async def test_price_drop_is_reposted_with_old_price(store):
    store.set_channel(1, 99)
    store.save_filter(1, 2, "standard", Criteria(min_ram=64), mention=True)

    channel = FakeChannel()
    poller = Poller(FakeBot(channel), store, fetch=lambda: [build_server(price="45")])
    await poller.run_once()
    assert len(channel.sent) == 1
    assert "45" in field_text(channel.sent[0][1], "Preis")

    cheaper = Poller(FakeBot(channel), store, fetch=lambda: [build_server(price="39.99")])
    report = await cheaper.run_once()

    assert report.posted == 1
    assert len(channel.sent) == 2
    price = field_text(channel.sent[1][1], "Preis")
    assert "vorher" in price
    assert "45" in price
    assert "39.99" in price


@pytest.mark.asyncio
async def test_paused_filter_posts_nothing(store):
    store.set_channel(1, 99)
    record = store.save_filter(1, 2, "standard", Criteria(min_ram=64), mention=False)
    store.set_active(1, 2, record.name, False)

    channel = FakeChannel()
    poller = Poller(FakeBot(channel), store, fetch=lambda: SERVERS)
    report = await poller.run_once()

    assert report.posted == 0
    assert channel.sent == []
