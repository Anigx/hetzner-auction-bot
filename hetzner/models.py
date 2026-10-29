"""Datenmodell der Hetzner-Serverbörse."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Server:
    id: int
    cpu_name: str
    sockets: int
    ram_gb: int
    ecc: bool
    storage_total_gb: int
    nvme_gb: int
    sata_gb: int
    hdd_gb: int
    location: str
    datacenter: str
    bandwidth_mbit: int
    traffic: str
    price_month_eur: Decimal
    price_hour_eur: Decimal
    setup_eur: Decimal
    extra_ips: int
    reduce_next_at: datetime | None
