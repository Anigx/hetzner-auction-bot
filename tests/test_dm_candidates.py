from decimal import Decimal

from hetzner_bot.engine import find_dm_candidates


def test_dm_filter_is_delivered_per_filter(make_server, make_filter):
    out = find_dm_candidates(
        [make_server()],
        [make_filter(delivery="dm", min_ram=64)],
        lambda f, s: False,
        lambda f, s: None,
    )
    assert len(out) == 1
    assert out[0].user_id == 2
    assert out[0].previous_price is None


def test_channel_filters_are_not_dm_candidates(make_server, make_filter):
    out = find_dm_candidates(
        [make_server()],
        [make_filter(delivery="channel", min_ram=64)],
        lambda f, s: False,
        lambda f, s: None,
    )
    assert out == []


def test_baselined_dm_is_not_sent(make_server, make_filter):
    out = find_dm_candidates(
        [make_server()],
        [make_filter(delivery="dm", min_ram=64)],
        lambda f, s: True,
        lambda f, s: None,
    )
    assert out == []


def test_dm_price_drop_is_sent_again(make_server, make_filter):
    out = find_dm_candidates(
        [make_server(price="39")],
        [make_filter(delivery="dm", min_ram=64)],
        lambda f, s: True,
        lambda f, s: Decimal("45"),
    )
    assert len(out) == 1
    assert out[0].previous_price == Decimal("45")


def test_dm_candidate_carries_the_users_vat(make_server, make_filter):
    out = find_dm_candidates(
        [make_server(price="39")],
        [make_filter(delivery="dm", min_ram=64)],
        lambda f, s: False,
        lambda f, s: None,
        lambda uid: 19.0,
    )
    assert out[0].vat_percent == 19.0
