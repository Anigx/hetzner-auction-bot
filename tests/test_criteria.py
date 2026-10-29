from decimal import Decimal

import pytest

from hetzner_bot.domain import Criteria, CriteriaError


def test_empty_criteria_is_rejected():
    with pytest.raises(CriteriaError):
        Criteria().validate()


def test_mention_alone_is_not_a_criterion():
    assert Criteria().has_criterion() is False
    assert Criteria(max_price=Decimal("50")).has_criterion() is True


def test_price_must_be_positive():
    with pytest.raises(CriteriaError):
        Criteria(max_price=Decimal("0")).validate()


def test_unknown_location_is_rejected():
    with pytest.raises(CriteriaError):
        Criteria(location="XYZ").validate()


def test_json_roundtrip():
    original = Criteria(max_price=Decimal("45.5"), min_ram=64, disk_type="nvme", ecc="ja")
    assert Criteria.from_json(original.to_json()) == original


def test_from_json_tolerates_unknown_keys():
    assert Criteria.from_json({"max_price": 50, "gibt_es_nicht": 1}) == Criteria(
        max_price=Decimal("50")
    )


def test_cpu_contains_alone_is_valid():
    Criteria(cpu_contains="ryzen").validate()


def test_validate_ignores_non_numeric_fields():
    Criteria(cpu_contains="ryzen", min_ram=64).validate()
