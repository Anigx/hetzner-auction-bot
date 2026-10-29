from decimal import Decimal

from filters import Criteria, FilterRecord
from poller import find_candidates


def server(id=10, price="45", **over):
    data = dict(
        id=id,
        cpu_name="AMD Ryzen 9 5950X",
        sockets=1,
        ram_gb=64,
        ecc=True,
        storage_total_gb=4096,
        nvme_gb=0,
        sata_gb=0,
        hdd_gb=8000,
        location="FSN",
        datacenter="FSN1-DC14",
        bandwidth_mbit=1000,
        traffic="unlimited",
        price_month_eur=Decimal(price),
        price_hour_eur=Decimal("0.05"),
        setup_eur=Decimal("0"),
        extra_ips=1,
        reduce_next_at=None,
    )
    data.update(over)
    from hetzner.models import Server

    return Server(**data)


def flt(id=1, guild=1, user=2, mention=True, active=True, **crit):
    return FilterRecord(
        id=id,
        guild_id=guild,
        user_id=user,
        name=f"f{id}",
        criteria=Criteria(**crit),
        mention=mention,
        active=active,
    )


def test_new_server_is_candidate():
    out = find_candidates([server()], [flt(min_ram=64)], lambda f, s: False, lambda g, s: None)
    assert len(out) == 1
    assert out[0].user_ids == (2,)
    assert out[0].previous_price is None


def test_baselined_server_is_not_posted():
    out = find_candidates([server()], [flt(min_ram=64)], lambda f, s: True, lambda g, s: None)
    assert out == []


def test_price_drop_is_posted_even_if_seen():
    out = find_candidates(
        [server(price="39")], [flt(min_ram=64)], lambda f, s: True, lambda g, s: Decimal("45")
    )
    assert len(out) == 1
    assert out[0].previous_price == Decimal("45")


def test_same_price_is_not_posted():
    out = find_candidates(
        [server(price="45")], [flt(min_ram=64)], lambda f, s: True, lambda g, s: Decimal("45")
    )
    assert out == []


def test_one_post_per_server_and_guild_with_two_filters():
    out = find_candidates(
        [server()], [flt(id=1, user=2), flt(id=2, user=3)], lambda f, s: False, lambda g, s: None
    )
    assert len(out) == 1
    assert out[0].filter_ids == (1, 2)
    assert out[0].user_ids == (2, 3)


def test_same_user_two_filters_pings_once():
    out = find_candidates(
        [server()], [flt(id=1, user=2), flt(id=2, user=2)], lambda f, s: False, lambda g, s: None
    )
    assert out[0].user_ids == (2,)


def test_inactive_filters_and_non_matches_are_ignored():
    out = find_candidates(
        [server()],
        [flt(active=False), flt(id=9, min_ram=512)],
        lambda f, s: False,
        lambda g, s: None,
    )
    assert out == []


def test_guilds_are_independent():
    out = find_candidates(
        [server()],
        [flt(id=1, guild=1), flt(id=2, guild=2)],
        lambda f, s: False,
        lambda g, s: None,
    )
    assert {c.guild_id for c in out} == {1, 2}
