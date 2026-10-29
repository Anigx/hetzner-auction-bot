"""Slash-Commands des Bots."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Literal, Sequence

import discord
from discord import app_commands
from discord.ext import commands

from filters import Criteria, CriteriaError, FilterRecord, matches
from hetzner.client import fetch_servers
from hetzner.models import Server

log = logging.getLogger(__name__)

DiskType = Literal["egal", "nvme", "sata", "hdd"]
Location = Literal["egal", "FSN", "NBG", "HEL"]
Ecc = Literal["egal", "ja"]


def require_guild_id(interaction: discord.Interaction) -> int:
    """Guild-ID für Commands, die jedes Mitglied nutzen darf."""
    guild = getattr(interaction, "guild", None)
    if guild is None:
        raise ValueError("Dieser Command funktioniert nur auf einem Discord-Server.")
    return int(guild.id)


def resolve_guild_id(interaction: discord.Interaction) -> int:
    """Guild-ID für Admin-Commands: verlangt 'Server verwalten'."""
    guild_id = require_guild_id(interaction)
    permissions = getattr(getattr(interaction, "user", None), "guild_permissions", None)
    if permissions is None or not permissions.manage_guild:
        raise PermissionError("Dafuer brauchst du das Recht 'Server verwalten'.")
    return guild_id


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


def snap_to_current(
    store, record: FilterRecord, servers: Sequence[Server]
) -> int:
    """Markiert alle aktuell passenden Server als gesehen, ohne sie zu posten."""
    ids = [server.id for server in servers if matches(record.criteria, server)]
    if ids:
        store.mark_seen(record.id, ids)
    return len(ids)


class Commands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _current_servers(self) -> list[Server]:
        if self.bot.last_servers:
            return self.bot.last_servers
        servers = await fetch_servers(self.bot.http, self.bot.config.auction_url)
        self.bot.last_servers = servers
        return servers

    @app_commands.command(name="setup", description="Legt fest, in welchen Kanal die Treffer kommen.")
    @app_commands.describe(channel="Kanal fuer Treffer aus der Serverboerse")
    async def setup(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        try:
            guild_id = resolve_guild_id(interaction)
        except (ValueError, PermissionError) as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        self.bot.store.set_channel(guild_id, channel.id)
        log.info("Kanal fuer Guild %s auf %s gesetzt", guild_id, channel.id)
        await interaction.response.send_message(
            f"Treffer landen ab jetzt in {channel.mention}.", ephemeral=True
        )

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

        record = self.bot.store.save_filter(
            guild_id, interaction.user.id, name.strip() or "standard", criteria, mention
        )

        try:
            servers = await self._current_servers()
        except Exception as exc:  # noqa: BLE001 - dem Nutzer eine klare Meldung geben
            log.warning("Snapshot fuer Baseline fehlgeschlagen: %s", exc)
            await interaction.followup.send(
                f"Filter '{record.name}' gespeichert. Die aktuelle Serverbörse konnte ich "
                "gerade nicht laden — ab jetzt melde ich neue Treffer.",
                ephemeral=True,
            )
            return

        count = snap_to_current(self.bot.store, record, servers)
        ping = "mit Ping" if mention else "ohne Ping"
        await interaction.followup.send(
            f"Filter '{record.name}' gespeichert ({ping}). "
            f"Aktuell passen {count} Server — ab jetzt melde ich neue.",
            ephemeral=True,
        )
