from decimal import Decimal

import pytest

from hetzner_bot.bot.cogs.watch import build_criteria, snap_to_current
from hetzner_bot.bot.texts import channel_warning
from hetzner_bot.domain import Criteria, CriteriaError


def test_build_criteria_maps_options():
    crit = build_criteria(
        max_price=45,
        min_ram=64,
        disk_type=None,
        location=None,
        cpu=None,
        min_disk=None,
        ecc=None,
        no_setup=None,
        min_bandwidth=None,
        min_cores=None,
    )
    assert crit.max_price == Decimal("45")
    assert crit.min_ram == 64
    assert crit.disk_type == "egal"


def test_build_criteria_without_any_criterion_raises():
    with pytest.raises(CriteriaError):
        build_criteria(
            max_price=None,
            min_ram=None,
            disk_type=None,
            location=None,
            cpu=None,
            min_disk=None,
            ecc=None,
            no_setup=None,
            min_bandwidth=None,
            min_cores=None,
        )


def test_build_criteria_accepts_cpu_only():
    crit = build_criteria(
        max_price=None,
        min_ram=None,
        disk_type=None,
        location=None,
        cpu="ryzen",
        min_disk=None,
        ecc=None,
        no_setup=None,
        min_bandwidth=None,
        min_cores=None,
    )
    assert crit.cpu_contains == "ryzen"


def test_snap_marks_all_current_matches(store, make_server):
    record = store.save_filter(1, 2, "standard", Criteria(min_ram=1), mention=False)
    servers = [make_server(id=10)]

    assert snap_to_current(store, record, servers) == 1
    assert store.is_seen(record.id, 10) is True
    assert store.baseline_price(1, 10) == Decimal("45")


def test_channel_warning():
    assert channel_warning(123) is None
    assert "/setup" in channel_warning(None)
