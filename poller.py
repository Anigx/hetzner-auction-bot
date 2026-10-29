"""Matching-Lauf: welche Server gehören in den Kanal?"""

from __future__ import annotations

import inspect
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Sequence

from filters import FilterRecord, matches
from hetzner.client import fetch_servers
from hetzner.models import Server
from notify import build_embed, mention_prefix
from store import Store

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
ALERT_AFTER_FAILURES = 3


@dataclass(frozen=True)
class PollReport:
    fetched: int = 0
    posted: int = 0
    queued: int = 0
    failed: bool = False


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


class Poller:
    """Holt die Auktion, ermittelt Treffer und stellt sie zu."""

    def __init__(
        self,
        bot: Any,
        store: Store,
        config: Any = None,
        fetch: Callable[[], Any] | None = None,
        max_posts: int | None = None,
    ) -> None:
        self.bot = bot
        self.store = store
        self.config = config
        self._fetch = fetch
        self.max_posts = max_posts or (getattr(config, "max_posts_per_run", 15))
        self.consecutive_failures = 0
        self._alerted = False

    def _write_heartbeat(self) -> None:
        """Schreibt den Zeitpunkt des letzten erfolgreichen Polls fuer den Healthcheck."""
        if self.config is None:
            return
        try:
            path = Path(self.config.database_path).parent / "last_poll"
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name("last_poll.tmp")
            tmp.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")
            os.replace(tmp, path)
        except OSError as exc:
            log.warning("Heartbeat konnte nicht geschrieben werden: %s", exc)

    async def _load(self) -> list[Server]:
        if self._fetch is None:
            return await fetch_servers(self.bot.http, self.config.auction_url)
        result = self._fetch()
        if inspect.isawaitable(result):
            return await result
        return result

    async def _notify_all_guilds(self, text: str) -> None:
        for record in self.store.list_filters():
            channel_id = self.store.get_channel(record.guild_id)
            channel = self.bot.get_channel(channel_id) if channel_id else None
            if channel is None:
                continue
            try:
                await channel.send(text)
            except Exception as exc:  # noqa: BLE001 - Ausfallmeldung darf nichts kippen
                log.warning("Ausfallmeldung an Guild %s fehlgeschlagen: %s", record.guild_id, exc)

    async def run_once(self) -> PollReport:
        try:
            servers = await self._load()
        except Exception as exc:  # noqa: BLE001 - jeder Fehler heisst: Lauf ueberspringen
            self.consecutive_failures += 1
            log.error("Auktionsdaten nicht abrufbar: %s", exc)
            self.bot.last_error = str(exc)
            if self.consecutive_failures >= ALERT_AFTER_FAILURES and not self._alerted:
                self._alerted = True
                minutes = self.consecutive_failures * getattr(self.config, "poll_minutes", 10)
                await self._notify_all_guilds(
                    f"Ich komme seit {minutes} Minuten nicht an die Daten der Serverbörse."
                )
            return PollReport(failed=True)

        self.consecutive_failures = 0
        self.bot.last_servers = servers
        self.bot.last_poll_at = datetime.now(UTC)
        self.bot.last_error = None
        self._write_heartbeat()
        if self._alerted:
            self._alerted = False
            await self._notify_all_guilds("Ich bin wieder online und beobachte die Serverbörse.")

        by_id = {server.id: server for server in servers}
        filters = self.store.list_filters()
        filters_by_id = {record.id: record for record in filters}
        max_posts = self.max_posts

        pending: list[Candidate] = []
        for item in self.store.queued():
            server = by_id.get(item.server_id)
            if server is None:
                self.store.dequeue(item.guild_id, item.server_id)
                continue
            previous = self.store.last_price(item.guild_id, item.server_id)
            if previous is not None and server.price_month_eur >= previous:
                self.store.dequeue(item.guild_id, item.server_id)
                continue
            records = [filters_by_id[fid] for fid in item.filter_ids if fid in filters_by_id]
            pending.append(
                Candidate(
                    guild_id=item.guild_id,
                    server=server,
                    filter_ids=item.filter_ids,
                    user_ids=tuple(sorted({r.user_id for r in records if r.mention})),
                    previous_price=previous,
                )
            )

        candidates = pending + find_candidates(
            servers, filters, self.store.is_seen, self.store.last_price
        )

        unique: list[Candidate] = []
        seen_keys: set[tuple[int, int]] = set()
        for candidate in candidates:
            key = (candidate.guild_id, candidate.server.id)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            unique.append(candidate)

        to_post = unique[:max_posts]
        for candidate in unique[max_posts:]:
            self.store.enqueue(
                candidate.guild_id, candidate.server.id, candidate.filter_ids
            )

        posted = 0
        for candidate in to_post:
            if await self._deliver(candidate):
                posted += 1

        return PollReport(
            fetched=len(servers),
            posted=posted,
            queued=len(self.store.queued()),
            failed=False,
        )

    async def _deliver(self, candidate: Candidate) -> bool:
        server = candidate.server
        guild_id = candidate.guild_id
        channel_id = self.store.get_channel(guild_id)
        channel = self.bot.get_channel(channel_id) if channel_id else None

        if channel is None:
            attempts = self.store.bump_attempts(guild_id, server.id)
            log.warning(
                "Kein Kanal fuer Guild %s (Versuch %s/%s)", guild_id, attempts, MAX_ATTEMPTS
            )
            if attempts >= MAX_ATTEMPTS:
                self.store.dequeue(guild_id, server.id)
                log.error("Treffer %s fuer Guild %s verworfen", server.id, guild_id)
            else:
                self.store.enqueue(guild_id, server.id, candidate.filter_ids)
            return False

        try:
            await channel.send(
                content=mention_prefix(candidate.user_ids) or None,
                embed=build_embed(server, candidate.previous_price),
            )
        except Exception as exc:  # noqa: BLE001 - ein kaputter Kanal darf den Lauf nicht toeten
            attempts = self.store.bump_attempts(guild_id, server.id)
            log.warning("Post fuer %s fehlgeschlagen (Versuch %s): %s", server.id, attempts, exc)
            if attempts >= MAX_ATTEMPTS:
                self.store.dequeue(guild_id, server.id)
            else:
                self.store.enqueue(guild_id, server.id, candidate.filter_ids)
            return False

        self.store.record_post(guild_id, server.id, server.price_month_eur)
        for filter_id in candidate.filter_ids:
            self.store.mark_seen(filter_id, [server.id])
        self.store.dequeue(guild_id, server.id)
        return True
