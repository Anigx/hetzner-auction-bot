"""Datensätze, die zwischen Speicher, Matching und Zustellung wandern."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from hetzner_bot.domain.criteria import Criteria
from hetzner_bot.domain.server import Server


@dataclass(frozen=True)
class FilterRecord:
    """Ein gespeicherter Filter einer Person."""

    id: int
    guild_id: int
    user_id: int
    name: str
    criteria: Criteria
    mention: bool
    active: bool = True
    baseline_pending: bool = False
    delivery: str = "channel"


DELIVERY_KINDS = ("channel", "dm")


@dataclass(frozen=True)
class Candidate:
    """Ein Server, der in einen Kanal gehört."""

    guild_id: int
    server: Server
    filter_ids: tuple[int, ...]
    user_ids: tuple[int, ...]
    previous_price: Decimal | None


@dataclass(frozen=True)
class QueuedItem:
    """Ein Treffer, der noch nicht zugestellt wurde."""

    guild_id: int
    server_id: int
    filter_ids: tuple[int, ...]
    attempts: int
