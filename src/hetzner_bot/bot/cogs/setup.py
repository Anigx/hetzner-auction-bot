"""/setup — Kanal festlegen."""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from hetzner_bot.bot.guards import resolve_guild_id

log = logging.getLogger(__name__)


class SetupCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="setup", description="Legt fest, in welchen Kanal die Treffer kommen."
    )
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
