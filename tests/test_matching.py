from decimal import Decimal

from hetzner_bot.domain import Criteria
from hetzner_bot.engine import matches


def test_price_boundary_is_inclusive(make_server):
    assert matches(Criteria(max_price=Decimal("45")), make_server()) is True
    assert matches(Criteria(max_price=Decimal("44.99")), make_server()) is False


def test_min_cores_uses_table_and_skips_unknown(make_server):
    assert matches(Criteria(min_cores=16), make_server()) is True
    assert matches(Criteria(min_cores=17), make_server()) is False
    assert matches(Criteria(min_cores=4), make_server(cpu_name="Unbekannt")) is False


def test_cpu_contains_is_case_insensitive(make_server):
    assert matches(Criteria(cpu_contains="ryzen 9"), make_server()) is True


def test_disk_type_requires_type_and_sums_that_type_only(make_server):
    assert matches(Criteria(disk_type="hdd", min_disk=Decimal("8")), make_server()) is True
    assert matches(Criteria(disk_type="nvme", min_disk=Decimal("1")), make_server()) is False
    assert matches(Criteria(disk_type="nvme"), make_server(nvme_gb=1000)) is True


def test_min_disk_without_type_uses_usable_total(make_server):
    assert matches(Criteria(min_disk=Decimal("4")), make_server(storage_total_gb=4096)) is True
    assert matches(Criteria(min_disk=Decimal("2")), make_server(storage_total_gb=1966)) is False


def test_no_setup_and_location_and_bandwidth(make_server):
    assert matches(Criteria(no_setup=True), make_server(setup_eur=Decimal("0"))) is True
    assert matches(Criteria(no_setup=True), make_server(setup_eur=Decimal("49"))) is False
    assert matches(Criteria(location="FSN"), make_server(location="FSN")) is True
    assert matches(Criteria(location="NBG"), make_server(location="FSN")) is False
    assert matches(Criteria(min_bandwidth=1000), make_server(bandwidth_mbit=1000)) is True
    assert matches(Criteria(min_bandwidth=1000), make_server(bandwidth_mbit=100)) is False


def test_ecc_and_all_criteria_together(make_server):
    assert matches(Criteria(ecc="ja"), make_server(ecc=False)) is False
    both = Criteria(max_price=Decimal("50"), min_ram=64, min_cores=16, ecc="ja")
    assert matches(both, make_server()) is True
    assert matches(both, make_server(ram_gb=32)) is False
