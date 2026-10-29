"""Der Lauf: holen, entscheiden, zustellen."""

from __future__ import annotations

import inspect
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from hetzner_bot.auction import fetch_servers
from hetzner_bot.delivery import build_embed, mention_prefix
from hetzner_bot.domain import Candidate, Server
from hetzner_bot.engine.candidates import find_candidates
from hetzner_bot.engine.matching import matches
from hetzner_bot.storage import Store

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
ALERT_AFTER_FAILURES = 3


@dataclass(frozen=True)
class PollReport:
    fetched: int = 0
    posted: int = 0
    queued: int = 0
    failed: bool = False


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
        self._apply_pending_baselines(filters, servers)

        filters_by_id = {record.id: record for record in filters}
        max_posts = self.max_posts

        pending = self._rebuild_queue(filters_by_id, by_id)

        candidates = pending + find_candidates(
            servers,
            filters,
            self.store.is_seen,
            self.store.last_price,
            self.store.baseline_price,
        )

        unique: list[Candidate] = []
        seen_keys: set[tuple[int, int]] = set()
        for candidate in candidates:
            key = (candidate.guild_id, candidate.server.id)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            unique.append(candidate)

        for candidate in unique[max_posts:]:
            self.store.enqueue(candidate.guild_id, candidate.server.id, candidate.filter_ids)

        posted = 0
        for candidate in unique[:max_posts]:
            if await self._deliver(candidate):
                posted += 1

        return PollReport(
            fetched=len(servers),
            posted=posted,
            queued=len(self.store.queued()),
            failed=False,
        )

    # -- Vorbereitung -----------------------------------------------------

    def _apply_pending_baselines(self, filters, servers: list[Server]) -> None:
        """Baseline nachholen, wenn sie beim Anlegen des Filters nicht ging."""
        for record in filters:
            if not record.baseline_pending:
                continue
            matching = [server for server in servers if matches(record.criteria, server)]
            self.store.mark_seen(record.id, [server.id for server in matching])
            for server in matching:
                self.store.record_baseline(
                    record.guild_id, server.id, server.price_month_eur
                )
            self.store.set_baseline_pending(record.id, False)
            log.info("Baseline fuer Filter %s nachgeholt (%s Server)", record.id, len(matching))

    def _rebuild_queue(self, filters_by_id, by_id) -> list[Candidate]:
        """Treffer aus der Warteschlange erneut prüfen — Server können verschwinden."""
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
        return pending

    # -- Zustellung -------------------------------------------------------

    async def _deliver(self, candidate: Candidate) -> bool:
        server = candidate.server
        guild_id = candidate.guild_id
        self.store.enqueue(guild_id, server.id, candidate.filter_ids)

        channel_id = self.store.get_channel(guild_id)
        channel = self.bot.get_channel(channel_id) if channel_id else None

        if channel is None:
            return self._retry_or_give_up(candidate, "kein Kanal eingerichtet")

        try:
            await channel.send(
                content=mention_prefix(candidate.user_ids) or None,
                embed=build_embed(server, candidate.previous_price),
            )
        except Exception as exc:  # noqa: BLE001 - ein kaputter Kanal darf den Lauf nicht toeten
            self.bot.last_error = f"Zustellung an Guild {guild_id} fehlgeschlagen: {exc}"
            return self._retry_or_give_up(candidate, f"Post fehlgeschlagen: {exc}")

        self.store.record_post(guild_id, server.id, server.price_month_eur)
        for filter_id in candidate.filter_ids:
            self.store.mark_seen(filter_id, [server.id])
        self.store.dequeue(guild_id, server.id)
        return True

    def _retry_or_give_up(self, candidate: Candidate, reason: str) -> bool:
        """Zaehlt einen Fehlversuch. Nach MAX_ATTEMPTS wird der Treffer verworfen und
        als gesehen markiert, damit er nicht in jeder Runde neu auftaucht."""
        guild_id = candidate.guild_id
        server_id = candidate.server.id
        attempts = self.store.bump_attempts(guild_id, server_id)

        if attempts >= MAX_ATTEMPTS:
            self.store.dequeue(guild_id, server_id)
            for filter_id in candidate.filter_ids:
                self.store.mark_seen(filter_id, [server_id])
            log.error(
                "Treffer %s fuer Guild %s nach %s Versuchen verworfen: %s",
                server_id,
                guild_id,
                attempts,
                reason,
            )
            return False

        log.warning(
            "Treffer %s fuer Guild %s, Versuch %s/%s: %s",
            server_id,
            guild_id,
            attempts,
            MAX_ATTEMPTS,
            reason,
        )
        return False

    # -- Infrastruktur ----------------------------------------------------

    async def _load(self) -> list[Server]:
        if self._fetch is None:
            return await fetch_servers(self.bot.http, self.config.auction_url)
        result = self._fetch()
        if inspect.isawaitable(result):
            return await result
        return result

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

    async def _notify_all_guilds(self, text: str) -> None:
        guild_ids = sorted({record.guild_id for record in self.store.list_filters()})
        for guild_id in guild_ids:
            channel_id = self.store.get_channel(guild_id)
            channel = self.bot.get_channel(channel_id) if channel_id else None
            if channel is None:
                continue
            try:
                await channel.send(text)
            except Exception as exc:  # noqa: BLE001 - Ausfallmeldung darf nichts kippen
                log.warning("Ausfallmeldung an Guild %s fehlgeschlagen: %s", guild_id, exc)
