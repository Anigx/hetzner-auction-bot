"""Deutsche Texte für Commands und Antworten."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from hetzner_bot.domain import Criteria, FilterRecord

BERLIN = ZoneInfo("Europe/Berlin")


def format_local(moment: datetime) -> str:
    return moment.astimezone(BERLIN).strftime("%d.%m.%Y %H:%M")


def criteria_parts(criteria: Criteria) -> list[str]:
    parts: list[str] = []
    if criteria.max_price is not None:
        parts.append(f"≤ {criteria.max_price} €/Monat")
    if criteria.min_ram is not None:
        parts.append(f"≥ {criteria.min_ram} GB RAM")
    if criteria.min_cores is not None:
        parts.append(f"≥ {criteria.min_cores} Kerne")
    if criteria.cpu_contains is not None:
        parts.append(f"CPU enthält '{criteria.cpu_contains}'")
    if criteria.min_disk is not None:
        suffix = "" if criteria.disk_type == "egal" else f" {criteria.disk_type.upper()}"
        parts.append(f"≥ {criteria.min_disk} TB{suffix}")
    elif criteria.disk_type != "egal":
        parts.append(criteria.disk_type.upper())
    if criteria.location != "egal":
        parts.append(criteria.location)
    if criteria.ecc == "ja":
        parts.append("ECC")
    if criteria.no_setup:
        parts.append("ohne Setup")
    if criteria.min_bandwidth is not None:
        parts.append(f"≥ {criteria.min_bandwidth} Mbit/s")
    return parts or ["alles"]


def describe_filter(record: FilterRecord, match_count: int) -> str:
    text = f"**{record.name}** — " + ", ".join(criteria_parts(record.criteria))
    text += f" · {match_count} passende Server"
    if record.mention:
        text += " · Ping an"
    if not record.active:
        text += " · pausiert"
    return text


def channel_warning(channel_id: int | None) -> str | None:
    """Hinweis, wenn fuer diese Guild noch kein Kanal eingerichtet ist."""
    if channel_id is None:
        return "Noch kein Kanal eingerichtet — ein Admin muss `/setup` ausführen."
    return None
