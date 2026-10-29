"""Entscheidung: welche Server gehören in den Kanal?

Reine Funktion, kein I/O — die Nachschlage-Funktionen werden hereingereicht.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Sequence

from hetzner_bot.domain import Candidate, FilterRecord, Server
from hetzner_bot.engine.matching import matches


@dataclass(frozen=True)
class DmCandidate:
    """Ein Server, der per Direktnachricht an eine Person geht."""

    user_id: int
    filter_id: int
    server: Server
    previous_price: Decimal | None


def find_candidates(
    servers: Sequence[Server],
    filters: Sequence[FilterRecord],
    is_seen: Callable[[int, int], bool],
    last_price: Callable[[int, int], Decimal | None],
    baseline_price: Callable[[int, int], Decimal | None] | None = None,
) -> list[Candidate]:
    """Ermittelt pro Guild, welche Server gepostet werden müssen.

    - Unbekannter Server: posten, außer alle passenden Filter haben ihn schon gesehen.
    - Bekannter Server: nur posten, wenn der Preis unter dem zuletzt geposteten liegt.
    - Server aus der Baseline (beim Filter-Anlegen gesehen): posten, wenn er unter
      den Baseline-Preis fällt, auch wenn kein Post vorher im Kanal stand.
    """
    baseline_of = baseline_price or (lambda _guild, _server: None)

    by_guild: dict[int, list[FilterRecord]] = {}
    for record in filters:
        if record.delivery == "dm":
            continue
        by_guild.setdefault(record.guild_id, []).append(record)

    candidates: list[Candidate] = []
    for guild_id, guild_filters in by_guild.items():
        active = [record for record in guild_filters if record.active]
        if not active:
            continue

        for server in servers:
            eligible = [record for record in active if matches(record.criteria, server)]
            if not eligible:
                continue

            previous = last_price(guild_id, server.id)
            if previous is None:
                baseline = baseline_of(guild_id, server.id)
                dropped_below_baseline = (
                    baseline is not None and server.price_month_eur < baseline
                )
                if not dropped_below_baseline and all(
                    is_seen(record.id, server.id) for record in eligible
                ):
                    continue
            elif server.price_month_eur >= previous:
                continue

            candidates.append(
                Candidate(
                    guild_id=guild_id,
                    server=server,
                    filter_ids=tuple(sorted(record.id for record in eligible)),
                    user_ids=tuple(
                        sorted({record.user_id for record in eligible if record.mention})
                    ),
                    previous_price=previous,
                )
            )

    candidates.sort(key=lambda c: (c.guild_id, c.server.price_month_eur, c.server.id))
    return candidates


def find_dm_candidates(
    servers: Sequence[Server],
    filters: Sequence[FilterRecord],
    is_seen: Callable[[int, int], bool],
    last_dm_price: Callable[[int, int], Decimal | None],
) -> list[DmCandidate]:
    """Treffer fuer Filter, die per DM zugestellt werden — Dedupe pro Filter.

    Baseline gilt wie im Kanal: beim Anlegen gesehene Server werden nicht noch
    einmal geschickt, es sei denn der Preis faellt unter den Baseline-Preis.
    """
    out: list[DmCandidate] = []
    for record in filters:
        if record.delivery != "dm" or not record.active:
            continue
        for server in servers:
            if not matches(record.criteria, server):
                continue

            previous = last_dm_price(record.id, server.id)
            if previous is None:
                if is_seen(record.id, server.id):
                    continue
            elif server.price_month_eur >= previous:
                continue

            out.append(
                DmCandidate(
                    user_id=record.user_id,
                    filter_id=record.id,
                    server=server,
                    previous_price=previous,
                )
            )

    out.sort(key=lambda c: (c.user_id, c.server.price_month_eur, c.server.id))
    return out
