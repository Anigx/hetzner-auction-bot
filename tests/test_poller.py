from decimal import Decimal

import pytest

from hetzner_bot.domain import Criteria
from hetzner_bot.engine import Poller


class FakeChannel:
    def __init__(self, fail=False):
        self.fail = fail
        self.sent = []
        self.attempts = 0

    async def send(self, content=None, embed=None):
        self.attempts += 1
        if self.fail:
            raise RuntimeError("keine Rechte")
        self.sent.append((content, embed))


class FakeBot:
    def __init__(self, channel, user=None):
        self.channel = channel
        self.user = user

    def get_channel(self, cid):
        return self.channel

    def get_user(self, uid):
        return self.user

    async def fetch_user(self, uid):
        return self.user


class FakeUser:
    def __init__(self, fail=False):
        self.fail = fail
        self.sent = []

    async def send(self, embed=None, content=None):
        if self.fail:
            raise RuntimeError("DMs geschlossen")
        self.sent.append(embed)


class FakeConfig:
    def __init__(self, tmp_path):
        self.database_path = tmp_path / "data" / "bot.sqlite3"
        self.max_posts_per_run = 15
        self.poll_minutes = 10
        self.auction_url = "https://example.invalid"


@pytest.mark.asyncio
async def test_run_posts_and_marks_seen(store, make_server):
    store.set_channel(1, 99)
    store.save_filter(1, 2, "standard", Criteria(min_ram=64), mention=True)
    channel = FakeChannel()
    poller = Poller(FakeBot(channel), store, fetch=lambda: [make_server()], max_posts=15)
    report = await poller.run_once()
    assert report.posted == 1
    assert channel.sent[0][0] == "<@2>"
    assert store.last_price(1, 10) == Decimal("45")


@pytest.mark.asyncio
async def test_second_run_posts_nothing(store, make_server):
    store.set_channel(1, 99)
    store.save_filter(1, 2, "standard", Criteria(min_ram=64), mention=False)
    channel = FakeChannel()
    poller = Poller(FakeBot(channel), store, fetch=lambda: [make_server()], max_posts=15)
    await poller.run_once()
    report = await poller.run_once()
    assert report.posted == 0
    assert len(channel.sent) == 1


@pytest.mark.asyncio
async def test_failed_send_is_queued_not_recorded(store, make_server):
    store.set_channel(1, 99)
    store.save_filter(1, 2, "standard", Criteria(min_ram=64), mention=False)
    poller = Poller(
        FakeBot(FakeChannel(fail=True)), store, fetch=lambda: [make_server()], max_posts=15
    )
    report = await poller.run_once()
    assert report.posted == 0
    assert report.queued == 1
    assert store.last_price(1, 10) is None
    assert len(store.queued()) == 1


@pytest.mark.asyncio
async def test_vanished_queued_server_is_dropped(store):
    store.set_channel(1, 99)
    store.save_filter(1, 2, "standard", Criteria(min_ram=64), mention=False)
    store.enqueue(1, 999, (1,))
    poller = Poller(FakeBot(FakeChannel()), store, fetch=lambda: [], max_posts=15)
    report = await poller.run_once()
    assert report.posted == 0
    assert store.queued() == []


@pytest.mark.asyncio
async def test_successful_run_writes_heartbeat(store, make_server, tmp_path):
    store.set_channel(1, 99)
    store.save_filter(1, 2, "standard", Criteria(min_ram=64), mention=False)
    poller = Poller(
        FakeBot(FakeChannel()), store, config=FakeConfig(tmp_path), fetch=lambda: [make_server()]
    )
    await poller.run_once()
    assert (tmp_path / "data" / "last_poll").exists()


@pytest.mark.asyncio
async def test_broken_channel_gives_up_after_three_attempts(store, make_server):
    store.set_channel(1, 99)
    store.save_filter(1, 2, "standard", Criteria(min_ram=64), mention=False)
    channel = FakeChannel(fail=True)
    poller = Poller(FakeBot(channel), store, fetch=lambda: [make_server()], max_posts=15)

    for _ in range(5):
        await poller.run_once()

    assert channel.attempts == 3
    assert store.queued() == []


@pytest.mark.asyncio
async def test_outage_message_is_sent_once_per_guild(store):
    store.set_channel(1, 99)
    store.save_filter(1, 2, "a", Criteria(min_ram=64), mention=False)
    store.save_filter(1, 3, "b", Criteria(min_ram=32), mention=False)
    channel = FakeChannel()

    async def failing_fetch():
        raise RuntimeError("kaputt")

    poller = Poller(FakeBot(channel), store, fetch=failing_fetch, max_posts=15)
    for _ in range(3):
        report = await poller.run_once()

    assert report.failed is True
    assert len(channel.sent) == 1
    assert "nicht an die Daten" in channel.sent[0][0]


@pytest.mark.asyncio
async def test_pending_baseline_is_applied_on_next_run(store, make_server):
    store.set_channel(1, 99)
    record = store.save_filter(1, 2, "standard", Criteria(min_ram=64), mention=False)
    store.set_baseline_pending(record.id, True)
    channel = FakeChannel()
    poller = Poller(FakeBot(channel), store, fetch=lambda: [make_server()], max_posts=15)

    await poller.run_once()

    assert channel.sent == []
    assert store.get_filter(1, 2, "standard").baseline_pending is False
    assert store.baseline_price(1, 10) == Decimal("45")


@pytest.mark.asyncio
async def test_dm_filter_sends_only_a_direct_message(store, make_server):
    store.set_channel(1, 99)
    store.save_filter(1, 2, "dm", Criteria(min_ram=64), mention=False, delivery="dm")
    channel = FakeChannel()
    user = FakeUser()
    poller = Poller(
        FakeBot(channel, user), store, fetch=lambda: [make_server()], max_posts=15
    )

    report = await poller.run_once()

    assert report.posted == 0
    assert report.dms == 1
    assert channel.sent == []
    assert len(user.sent) == 1
    assert store.last_dm_price(store.list_filters(1, 2)[0].id, 10) == Decimal("45")


@pytest.mark.asyncio
async def test_closed_dms_do_not_crash_and_are_retried(store, make_server):
    store.set_channel(1, 99)
    store.save_filter(1, 2, "dm", Criteria(min_ram=64), mention=False, delivery="dm")
    channel = FakeChannel()
    user = FakeUser(fail=True)
    poller = Poller(
        FakeBot(channel, user), store, fetch=lambda: [make_server()], max_posts=15
    )

    report = await poller.run_once()

    assert report.dms == 0
    assert store.last_dm_price(store.list_filters(1, 2)[0].id, 10) is None
