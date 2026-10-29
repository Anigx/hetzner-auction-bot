from decimal import Decimal

import pytest

from cogs.commands import build_criteria, channel_warning, snap_to_current
from filters import Criteria, CriteriaError
from hetzner.models import Server
from store import Store


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


def test_snap_marks_all_current_matches(tmp_path):
    store = Store(tmp_path / "t.sqlite3")
    store.init_schema()
    rec = store.save_filter(1, 2, "standard", Criteria(min_ram=1), mention=False)
    servers = [
        Server(
            id=10,
            cpu_name="X",
            sockets=1,
            ram_gb=64,
            ecc=True,
            storage_total_gb=1000,
            nvme_gb=0,
            sata_gb=0,
            hdd_gb=0,
            location="FSN",
            datacenter="FSN1-DC1",
            bandwidth_mbit=1000,
            traffic="unlimited",
            price_month_eur=Decimal("45"),
            price_hour_eur=Decimal("0.05"),
            setup_eur=Decimal("0"),
            extra_ips=0,
            reduce_next_at=None,
        )
    ]
    assert snap_to_current(store, rec, servers) == 1
    assert store.is_seen(rec.id, 10) is True
    assert store.baseline_price(1, 10) == Decimal("45")


def test_channel_warning():
    assert channel_warning(123) is None
    assert "/setup" in channel_warning(None)
