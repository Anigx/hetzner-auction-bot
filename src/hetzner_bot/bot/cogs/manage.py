"""/filters, /unwatch, /pause, /resume, /status."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from hetzner_bot.auction.cpus import unknown_cpu_names
from hetzner_bot.bot.guards import require_guild_id
from hetzner_bot.bot.texts import (
    HELP_TEXT,
    channel_warning,
    describe_filter,
    format_local,
    format_match_line,
    guild_count_warning,
)
from hetzner_bot.engine.matching import matches


class ManageCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="Erklaert Befehle, Filter und Zustellung.")
    async def help_cmd(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(HELP_TEXT, ephemeral=True)

    @app_commands.command(
        name="matches", description="Zeigt Server, die gerade zu deinen Filtern passen."
    )
    async def matches_cmd(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            guild_id = require_guild_id(interaction)
        except ValueError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return

        records = self.bot.store.list_filters(
            guild_id, interaction.user.id, active_only=True
        )
        if not records:
            await interaction.followup.send(
                "Du hast keinen aktiven Filter. Leg einen mit `/watch` an.", ephemeral=True
            )
            return

        try:
            servers = await self.bot.current_servers()
        except Exception as exc:  # noqa: BLE001 - dem Nutzer eine klare Meldung geben
            await interaction.followup.send(
                f"Serverbörse gerade nicht erreichbar: {exc}", ephemeral=True
            )
            return

        hits = {
            server.id: server
            for record in records
            for server in servers
            if matches(record.criteria, server)
        }
        if not hits:
            await interaction.followup.send(
                "Gerade passt kein Server zu deinen Filtern.", ephemeral=True
            )
            return

        ordered = sorted(hits.values(), key=lambda s: (s.price_month_eur, s.id))
        lines = [f"**{len(ordered)} Server passen gerade:**"]
        lines += [format_match_line(server) for server in ordered[:8]]
        if len(ordered) > 8:
            lines.append(f"… und {len(ordered) - 8} weitere")
        await interaction.followup.send("\n".join(lines), ephemeral=True)

    @app_commands.command(name="filters", description="Zeigt deine gespeicherten Filter.")
    async def list_filters_cmd(self, interaction: discord.Interaction) -> None:
        try:
            guild_id = require_guild_id(interaction)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        records = self.bot.store.list_filters(guild_id, interaction.user.id)
        if not records:
            await interaction.response.send_message(
                "Du hast noch keinen Filter. Leg einen mit `/watch` an.", ephemeral=True
            )
            return

        servers = self.bot.last_servers
        lines = [
            describe_filter(
                record, sum(1 for server in servers if matches(record.criteria, server))
            )
            for record in records
        ]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="unwatch", description="Loescht einen deiner Filter.")
    @app_commands.describe(name="Name des Filters")
    async def unwatch(self, interaction: discord.Interaction, name: str = "standard") -> None:
        try:
            guild_id = require_guild_id(interaction)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        if self.bot.store.delete_filter(guild_id, interaction.user.id, name):
            text = f"Filter '{name}' geloescht."
        else:
            text = f"Filter '{name}' nicht gefunden."
        await interaction.response.send_message(text, ephemeral=True)

    @app_commands.command(name="pause", description="Pausiert einen Filter, ohne ihn zu loeschen.")
    @app_commands.describe(name="Name des Filters")
    async def pause(self, interaction: discord.Interaction, name: str = "standard") -> None:
        await self._set_active(interaction, name, False)

    @app_commands.command(name="resume", description="Aktiviert einen pausierten Filter wieder.")
    @app_commands.describe(name="Name des Filters")
    async def resume(self, interaction: discord.Interaction, name: str = "standard") -> None:
        await self._set_active(interaction, name, True)

    async def _set_active(
        self, interaction: discord.Interaction, name: str, active: bool
    ) -> None:
        try:
            guild_id = require_guild_id(interaction)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        if self.bot.store.set_active(guild_id, interaction.user.id, name, active):
            text = f"Filter '{name}' ist jetzt {'aktiv' if active else 'pausiert'}."
        else:
            text = f"Filter '{name}' nicht gefunden."
        await interaction.response.send_message(text, ephemeral=True)

    @app_commands.command(name="status", description="Zeigt den Zustand des Bots.")
    async def status(self, interaction: discord.Interaction) -> None:
        try:
            guild_id = require_guild_id(interaction)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        servers = self.bot.last_servers
        last_poll = self.bot.last_poll_at
        last_error = self.bot.last_error
        active_filters = self.bot.store.list_filters(guild_id, active_only=True)
        next_reduce = min(
            (server.reduce_next_at for server in servers if server.reduce_next_at is not None),
            default=None,
        )
        channel_state = (
            "eingerichtet"
            if channel_warning(self.bot.store.get_channel(guild_id)) is None
            else "fehlt"
        )

        lines = [
            f"Letzter Abruf: {format_local(last_poll) if last_poll else 'noch keiner'}",
            f"Server im Snapshot: {len(servers)}",
            f"Aktive Filter hier: {len(active_filters)}",
            f"Kanal: {channel_state}",
            f"Nächster Preisfall: {format_local(next_reduce) if next_reduce else 'unbekannt'}",
            f"Wartende Treffer: {len(self.bot.store.queued())}",
        ]
        unknown = unknown_cpu_names(server.cpu_name for server in servers)
        if unknown:
            lines.append(f"Unbekannte CPUs (Kern-Filter greift dort nicht): {', '.join(unknown)}")
        guild_warning = guild_count_warning(len(self.bot.guilds))
        if guild_warning:
            lines.append(guild_warning)
        if last_error:
            lines.append(f"Letzter Fehler: {last_error}")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)
