"""Filterkriterien, Validierung und das Domänenobjekt eines gespeicherten Filters."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

from hetzner.cpus import cores_for
from hetzner.models import Server

DISK_TYPES = ("egal", "nvme", "sata", "hdd")
LOCATIONS = ("egal", "FSN", "NBG", "HEL")
ECC_VALUES = ("egal", "ja")

_CRITERION_FIELDS = (
    "max_price",
    "min_ram",
    "min_cores",
    "cpu_contains",
    "min_disk",
    "min_bandwidth",
)


class CriteriaError(ValueError):
    """Ein Filter ist ungültig."""


@dataclass(frozen=True)
class Criteria:
    max_price: Decimal | None = None
    min_ram: int | None = None
    min_cores: int | None = None
    cpu_contains: str | None = None
    min_disk: Decimal | None = None
    disk_type: str = "egal"
    location: str = "egal"
    ecc: str = "egal"
    no_setup: bool = False
    min_bandwidth: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "disk_type", str(self.disk_type).strip().lower() or "egal")
        object.__setattr__(self, "location", str(self.location).strip().upper() if self.location else "egal")
        if self.location.lower() == "egal":
            object.__setattr__(self, "location", "egal")
        object.__setattr__(self, "ecc", str(self.ecc).strip().lower() or "egal")

        cpu = self.cpu_contains
        if cpu is not None:
            cpu = cpu.strip()
            object.__setattr__(self, "cpu_contains", cpu or None)

        for name in ("max_price", "min_disk"):
            value = getattr(self, name)
            if isinstance(value, (int, float, str)):
                object.__setattr__(self, name, Decimal(str(value)))

    def has_criterion(self) -> bool:
        if any(getattr(self, name) is not None for name in _CRITERION_FIELDS):
            return True
        return (
            self.disk_type != "egal"
            or self.location != "egal"
            or self.ecc != "egal"
            or self.no_setup
        )

    def validate(self) -> None:
        for name in _CRITERION_FIELDS:
            value = getattr(self, name)
            if value is not None and value <= 0:
                raise CriteriaError(f"{name} muss groesser als 0 sein")

        if self.disk_type not in DISK_TYPES:
            raise CriteriaError(f"Unbekannter Plattentyp: {self.disk_type!r}")
        if self.location not in LOCATIONS:
            raise CriteriaError(f"Unbekannter Standort: {self.location!r}")
        if self.ecc not in ECC_VALUES:
            raise CriteriaError(f"Unbekannter ECC-Wert: {self.ecc!r}")
        if not self.has_criterion():
            raise CriteriaError("Mindestens ein Kriterium muss gesetzt sein")

    def to_json(self) -> dict[str, Any]:
        return {
            "max_price": None if self.max_price is None else str(self.max_price),
            "min_ram": self.min_ram,
            "min_cores": self.min_cores,
            "cpu_contains": self.cpu_contains,
            "min_disk": None if self.min_disk is None else str(self.min_disk),
            "disk_type": self.disk_type,
            "location": self.location,
            "ecc": self.ecc,
            "no_setup": self.no_setup,
            "min_bandwidth": self.min_bandwidth,
        }

    @classmethod
    def from_json(cls, raw: Mapping[str, Any]) -> "Criteria":
        return cls(
            max_price=None if raw.get("max_price") is None else Decimal(str(raw["max_price"])),
            min_ram=None if raw.get("min_ram") is None else int(raw["min_ram"]),
            min_cores=None if raw.get("min_cores") is None else int(raw["min_cores"]),
            cpu_contains=raw.get("cpu_contains"),
            min_disk=None if raw.get("min_disk") is None else Decimal(str(raw["min_disk"])),
            disk_type=raw.get("disk_type") or "egal",
            location=raw.get("location") or "egal",
            ecc=raw.get("ecc") or "egal",
            no_setup=bool(raw.get("no_setup") or False),
            min_bandwidth=None if raw.get("min_bandwidth") is None else int(raw["min_bandwidth"]),
        )


@dataclass(frozen=True)
class FilterRecord:
    id: int
    guild_id: int
    user_id: int
    name: str
    criteria: Criteria
    mention: bool
    active: bool = True


def matches(criteria: Criteria, server: Server) -> bool:
    """Prüft, ob ein Server alle gesetzten Kriterien erfüllt. Nicht gesetzte zählen nicht."""
    if criteria.max_price is not None and server.price_month_eur > criteria.max_price:
        return False

    if criteria.min_ram is not None and server.ram_gb < criteria.min_ram:
        return False

    if criteria.min_cores is not None:
        cores = cores_for(server.cpu_name)
        if cores is None or cores < criteria.min_cores:
            return False

    if criteria.cpu_contains is not None:
        if criteria.cpu_contains.lower() not in server.cpu_name.lower():
            return False

    if criteria.disk_type != "egal":
        pool = {
            "nvme": server.nvme_gb,
            "sata": server.sata_gb,
            "hdd": server.hdd_gb,
        }[criteria.disk_type]
        if pool <= 0:
            return False
        if criteria.min_disk is not None and pool < criteria.min_disk * 1000:
            return False
    elif criteria.min_disk is not None:
        if server.storage_total_gb < criteria.min_disk * 1000:
            return False

    if criteria.location != "egal" and server.location != criteria.location:
        return False

    if criteria.ecc == "ja" and not server.ecc:
        return False

    if criteria.no_setup and server.setup_eur != 0:
        return False

    if criteria.min_bandwidth is not None and server.bandwidth_mbit < criteria.min_bandwidth:
        return False

    return True
