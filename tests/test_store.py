from decimal import Decimal

from hetzner_bot.domain import Criteria


def test_channel_roundtrip(store):
    assert store.get_channel(1) is None
    store.set_channel(1, 99)
    assert store.get_channel(1) == 99


def test_save_filter_replaces_by_name(store):
    store.save_filter(1, 2, "standard", Criteria(min_ram=64), mention=False)
    record = store.save_filter(1, 2, "standard", Criteria(min_ram=128), mention=True)
    assert record.criteria.min_ram == 128
    assert record.mention is True
    assert len(store.list_filters(1, 2)) == 1


def test_delete_and_pause(store):
    store.save_filter(1, 2, "standard", Criteria(min_ram=64), mention=False)
    assert store.set_active(1, 2, "standard", False) is True
    assert store.list_filters(1, 2, active_only=True) == []
    assert store.delete_filter(1, 2, "standard") is True
    assert store.get_filter(1, 2, "standard") is None


def test_seen_is_per_filter(store):
    a = store.save_filter(1, 2, "a", Criteria(min_ram=64), mention=False)
    b = store.save_filter(1, 3, "b", Criteria(min_ram=64), mention=False)
    store.mark_seen(a.id, [10, 11])
    assert store.is_seen(a.id, 10) is True
    assert store.is_seen(b.id, 10) is False


def test_posts_are_per_guild(store):
    store.record_post(1, 10, Decimal("45"))
    assert store.last_price(1, 10) == Decimal("45")
    assert store.last_price(2, 10) is None


def test_queue_roundtrip_and_attempts(store):
    store.enqueue(1, 10, (5, 6))
    item = store.queued()[0]
    assert item.filter_ids == (5, 6)
    assert store.bump_attempts(1, 10) == 1
    store.dequeue(1, 10)
    assert store.queued() == []


def test_baseline_price_roundtrip(store):
    assert store.baseline_price(1, 10) is None
    store.record_baseline(1, 10, Decimal("45"))
    assert store.baseline_price(1, 10) == Decimal("45")
    assert store.baseline_price(2, 10) is None


def test_baseline_pending_flag(store):
    record = store.save_filter(1, 2, "s", Criteria(min_ram=64), mention=False)
    assert record.baseline_pending is False
    store.set_baseline_pending(record.id, True)
    assert store.get_filter(1, 2, "s").baseline_pending is True


def test_delivery_is_stored_and_can_be_changed(store):
    record = store.save_filter(1, 2, "dm", Criteria(min_ram=64), mention=False, delivery="dm")
    assert record.delivery == "dm"
    record = store.save_filter(
        1, 2, "dm", Criteria(min_ram=64), mention=False, delivery="channel"
    )
    assert record.delivery == "channel"


def test_dm_price_history_is_per_filter(store):
    store.record_dm_post(7, 10, Decimal("45"))
    assert store.last_dm_price(7, 10) == Decimal("45")
    assert store.last_dm_price(8, 10) is None


def test_user_vat_roundtrip(store):
    assert store.get_user_vat(1) is None
    store.set_user_vat(1, 19)
    assert store.get_user_vat(1) == 19
    store.set_user_vat(1, 8.1)
    assert store.get_user_vat(1) == 8.1
