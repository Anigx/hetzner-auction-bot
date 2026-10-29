"""Abruf und Parsing der Hetzner-Auktionsdaten."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from hetzner.models import Server

AUCTION_URL = "https://www.hetzner.com/_resources/app/data/app/live_data_sb.json"

_LOCATIONS = {"FSN", "NBG", "HEL"}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _sum_gb(values: Any) -> int:
    if not isinstance(values, list):
        return 0
    return sum(_as_int(item) for item in values)


def _location_from_datacenter(datacenter: str) -> str:
    prefix = datacenter.split("-", 1)[0].rstrip("0123456789")
    return prefix if prefix in _LOCATIONS else ""


def _parse_server(raw: dict[str, Any]) -> Server:
    hardware = _as_dict(raw.get("Hardware"))
    cpu = _as_dict(hardware.get("CPU"))
    ram = _as_dict(hardware.get("RAM"))
    storage = _as_dict(hardware.get("Storage"))
    disk_details = _as_dict(storage.get("Details"))
    details = _as_dict(raw.get("Details"))
    datacenter = str(_as_dict(details.get("Datacenter")).get("Name") or "")
    prices = _as_dict(raw.get("Prices"))
    timer = _as_dict(raw.get("Timer"))

    reduce_ts = _as_int(timer.get("ReduceNextTimestamp"), 0)
    reduce_next_at = datetime.fromtimestamp(reduce_ts, tz=UTC) if reduce_ts > 0 else None

    return Server(
        id=_as_int(raw.get("Id")),
        cpu_name=str(cpu.get("Name") or "").strip(),
        sockets=_as_int(cpu.get("CoreCount")),
        ram_gb=_as_int(ram.get("Size")),
        ecc=ram.get("ecc") is True,
        storage_total_gb=_as_int(storage.get("Size")),
        nvme_gb=_sum_gb(disk_details.get("nvme")),
        sata_gb=_sum_gb(disk_details.get("sata")),
        hdd_gb=_sum_gb(disk_details.get("hdd")),
        location=_location_from_datacenter(datacenter),
        datacenter=datacenter,
        bandwidth_mbit=_as_int(details.get("Bandwidth")),
        traffic=str(details.get("Traffic") or ""),
        price_month_eur=_as_decimal(_as_dict(prices.get("monthly")).get("EUR")),
        price_hour_eur=_as_decimal(_as_dict(prices.get("hourly")).get("EUR")),
        setup_eur=_as_decimal(_as_dict(prices.get("setup")).get("EUR")),
        extra_ips=_as_int(_as_dict(raw.get("IPPrices")).get("Amount")),
        reduce_next_at=reduce_next_at,
    )


def parse_servers(payload: dict[str, Any]) -> list[Server]:
    """Wandelt die Auktions-JSON in Server-Objekte. Wirft bei kaputten Einträgen nicht."""
    raw_servers = payload.get("server")
    if not isinstance(raw_servers, list):
        return []
    return [_parse_server(item) for item in raw_servers if isinstance(item, dict)]
