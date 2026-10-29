"""Regeln: erfüllt ein Server einen Filter?"""

from __future__ import annotations

import logging

from hetzner_bot.auction.cpus import cores_for
from hetzner_bot.domain import Criteria, Server
from hetzner_bot.pricing import with_vat

log = logging.getLogger(__name__)

_warned_unknown_cpus: set[str] = set()


def matches(criteria: Criteria, server: Server, vat_percent: float = 0) -> bool:
    """Prüft, ob ein Server alle gesetzten Kriterien erfüllt. Nicht gesetzte zählen nicht."""
    if criteria.max_price is not None and with_vat(server.price_month_eur, vat_percent) > criteria.max_price:
        return False

    if criteria.min_ram is not None and server.ram_gb < criteria.min_ram:
        return False

    if criteria.min_cores is not None:
        cores = cores_for(server.cpu_name)
        if cores is None:
            _warn_unknown_cpu(server.cpu_name)
            return False
        if cores < criteria.min_cores:
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


def _warn_unknown_cpu(cpu_name: str) -> None:
    """Einmal pro Modell warnen, nicht bei jedem Lauf."""
    key = cpu_name.strip().lower()
    if key in _warned_unknown_cpus:
        return
    _warned_unknown_cpus.add(key)
    log.warning("Unbekannte CPU %r: min_cores greift nicht. In hetzner/cpus.py ergaenzen.", cpu_name)
