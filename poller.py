"""Matching-Lauf: welche Server gehören in den Kanal?"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Sequence

from filters import FilterRecord, matches
from hetzner.models import Server


@dataclass(frozen=True)
class Candidate:
    guild_id: int
    server: Server
    filter_ids: tuple[int, ...]
    user_ids: tuple[int, ...]
    previous_price: Decimal | None


def find_candidates(
    servers: Sequence[Server],
    filters: Sequence[FilterRecord],
    is_seen: Callable[[int, int], bool],
    last_price: Callable[[int, int], Decimal | None],
) -> list[Candidate]:
    """Ermittelt pro Guild, welche Server gepostet werden müssen.

    - Unbekannter Server: posten, außer alle passenden Filter haben ihn schon gesehen.
    - Bekannter Server: nur posten, wenn der Preis unter dem zuletzt geposteten liegt.
    """
    by_guild: dict[int, list[FilterRecord]] = {}
    for record in filters:
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
                if all(is_seen(record.id, server.id) for record in eligible):
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
