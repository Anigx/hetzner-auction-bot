from decimal import Decimal

from hetzner_bot.engine import find_candidates


def test_new_server_is_candidate(make_server, make_filter):
    out = find_candidates(
        [make_server()], [make_filter(min_ram=64)], lambda f, s: False, lambda g, s: None
    )
    assert len(out) == 1
    assert out[0].user_ids == (2,)
    assert out[0].previous_price is None


def test_baselined_server_is_not_posted(make_server, make_filter):
    out = find_candidates(
        [make_server()], [make_filter(min_ram=64)], lambda f, s: True, lambda g, s: None
    )
    assert out == []


def test_price_drop_is_posted_even_if_seen(make_server, make_filter):
    out = find_candidates(
        [make_server(price="39")],
        [make_filter(min_ram=64)],
        lambda f, s: True,
        lambda g, s: Decimal("45"),
    )
    assert len(out) == 1
    assert out[0].previous_price == Decimal("45")


def test_same_price_is_not_posted(make_server, make_filter):
    out = find_candidates(
        [make_server(price="45")],
        [make_filter(min_ram=64)],
        lambda f, s: True,
        lambda g, s: Decimal("45"),
    )
    assert out == []


def test_one_post_per_server_and_guild_with_two_filters(make_server, make_filter):
    out = find_candidates(
        [make_server()],
        [make_filter(id=1, user=2), make_filter(id=2, user=3)],
        lambda f, s: False,
        lambda g, s: None,
    )
    assert len(out) == 1
    assert out[0].filter_ids == (1, 2)
    assert out[0].user_ids == (2, 3)


def test_same_user_two_filters_pings_once(make_server, make_filter):
    out = find_candidates(
        [make_server()],
        [make_filter(id=1, user=2), make_filter(id=2, user=2)],
        lambda f, s: False,
        lambda g, s: None,
    )
    assert out[0].user_ids == (2,)


def test_inactive_filters_and_non_matches_are_ignored(make_server, make_filter):
    out = find_candidates(
        [make_server()],
        [make_filter(active=False), make_filter(id=9, min_ram=512)],
        lambda f, s: False,
        lambda g, s: None,
    )
    assert out == []


def test_guilds_are_independent(make_server, make_filter):
    out = find_candidates(
        [make_server()],
        [make_filter(id=1, guild=1), make_filter(id=2, guild=2)],
        lambda f, s: False,
        lambda g, s: None,
    )
    assert {c.guild_id for c in out} == {1, 2}


def test_baselined_price_drop_is_posted(make_server, make_filter):
    out = find_candidates(
        [make_server(price="39")],
        [make_filter(min_ram=64)],
        lambda f, s: True,
        lambda g, s: None,
        lambda g, s: Decimal("45"),
    )
    assert len(out) == 1
    assert out[0].previous_price is None


def test_baselined_same_price_is_not_posted(make_server, make_filter):
    out = find_candidates(
        [make_server(price="45")],
        [make_filter(min_ram=64)],
        lambda f, s: True,
        lambda g, s: None,
        lambda g, s: Decimal("45"),
    )
    assert out == []
