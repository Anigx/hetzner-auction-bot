"""/watch — Filter anlegen und Baseline ziehen."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Literal, Sequence

import discord
from discord import app_commands
from discord.ext import commands

from hetzner_bot.bot.guards import require_guild_id
from hetzner_bot.bot.texts import channel_warning
from hetzner_bot.domain import Criteria, CriteriaError, FilterRecord, Server
from hetzner_bot.engine.matching import matches

log = logging.getLogger(__name__)

DiskType = Literal["egal", "nvme", "sata", "hdd"]
Location = Literal["egal", "FSN", "NBG", "HEL"]
Ecc = Literal["egal", "ja"]


def _decimal_or_none(value: float | int | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def build_criteria(
    max_price: float | None,
    min_ram: int | None,
    disk_type: str | None,
    location: str | None,
    cpu: str | None,
    min_disk: float | None,
    ecc: str | None,
    no_setup: bool | None,
    min_bandwidth: int | None,
    min_cores: int | None,
) -> Criteria:
    criteria = Criteria(
        max_price=_decimal_or_none(max_price),
        min_ram=min_ram,
        min_cores=min_cores,
        cpu_contains=cpu,
        min_disk=_decimal_or_none(min_disk),
        disk_type=disk_type or "egal",
        location=location or "egal",
        ecc=ecc or "egal",
        no_setup=bool(no_setup),
        min_bandwidth=min_bandwidth,
    )
    criteria.validate()
    return criteria


def snap_to_current(store, record: FilterRecord, servers: Sequence[Server]) -> int:
    """Markiert alle aktuell passenden Server als gesehen und merkt sich ihren Preis."""
    matching = [server for server in servers if matches(record.criteria, server)]
    if matching:
        store.mark_seen(record.id, [server.id for server in matching])
        for server in matching:
            store.record_baseline(record.guild_id, server.id, server.price_month_eur)
    store.set_baseline_pending(record.id, False)
    return len(matching)


def filter_quota_exceeded(store, guild_id: int, user_id: int, name: str, limit: int) -> bool:
    """Neue Filter sind begrenzt; ein vorhandener Name darf immer ersetzt werden."""
    if limit is None or limit <= 0:
        return False
    if store.get_filter(guild_id, user_id, name) is not None:
        return False
    return len(store.list_filters(guild_id, user_id)) >= limit


class WatchCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="watch", description="Legt einen Filter fuer die Serverboerse an.")
    @app_commands.describe(
        name="Name des Filters (wird ersetzt, wenn er schon existiert)",
        max_price="Hoechstpreis pro Monat in Euro",
        min_ram="Mindest-RAM in GB",
        min_cores="Mindestanzahl Kerne",
        cpu="CPU-Name muss diesen Text enthalten",
        min_disk="Mindest-Plattengroesse in TB",
        disk_type="Plattentyp",
        location="Standort",
        ecc="Nur Server mit ECC-RAM",
        no_setup="Nur Server ohne Setup-Gebuehr",
        min_bandwidth="Mindest-Anbindung in Mbit/s",
        mention="Bei Treffern taggen",
    )
    async def watch(
        self,
        interaction: discord.Interaction,
        name: str = "standard",
        max_price: float | None = None,
        min_ram: int | None = None,
        min_cores: int | None = None,
        cpu: str | None = None,
        min_disk: float | None = None,
        disk_type: DiskType | None = None,
        location: Location | None = None,
        ecc: Ecc | None = None,
        no_setup: bool | None = None,
        min_bandwidth: int | None = None,
        mention: bool = False,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        try:
            guild_id = require_guild_id(interaction)
            criteria = build_criteria(
                max_price=max_price,
                min_ram=min_ram,
                disk_type=disk_type,
                location=location,
                cpu=cpu,
                min_disk=min_disk,
                ecc=ecc,
                no_setup=no_setup,
                min_bandwidth=min_bandwidth,
                min_cores=min_cores,
            )
        except (ValueError, PermissionError, CriteriaError) as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return

        clean_name = name.strip() or "standard"
        limit = self.bot.config.max_filters_per_user
        if filter_quota_exceeded(
            self.bot.store, guild_id, interaction.user.id, clean_name, limit
        ):
            await interaction.followup.send(
                f"Du hast schon {limit} Filter. Loesche einen mit `/unwatch` "
                "oder ueberschreibe einen vorhandenen Namen.",
                ephemeral=True,
            )
            return

        record = self.bot.store.save_filter(
            guild_id, interaction.user.id, clean_name, criteria, mention
        )

        try:
            servers = await self.bot.current_servers()
        except Exception as exc:  # noqa: BLE001 - dem Nutzer eine klare Meldung geben
            log.warning("Snapshot fuer Baseline fehlgeschlagen: %s", exc)
            self.bot.store.set_baseline_pending(record.id, True)
            await interaction.followup.send(
                f"Filter '{record.name}' gespeichert. Die aktuelle Serverbörse konnte ich "
                "gerade nicht laden — die Baseline hole ich beim nächsten Abruf nach, "
                "damit der Kanal nicht mit Altbestand geflutet wird.",
                ephemeral=True,
            )
            return

        count = snap_to_current(self.bot.store, record, servers)
        ping = "mit Ping" if mention else "ohne Ping"
        text = (
            f"Filter '{record.name}' gespeichert ({ping}). "
            f"Aktuell passen {count} Server — ab jetzt melde ich neue."
        )
        warning = channel_warning(self.bot.store.get_channel(guild_id))
        if warning:
            text += f"\n{warning}"
        await interaction.followup.send(text, ephemeral=True)
