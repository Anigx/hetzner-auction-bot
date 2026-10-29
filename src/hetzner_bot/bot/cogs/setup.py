"""SetupCog — /setup"""

from __future__ import annotations

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from hetzner_bot.bot.guards import ensure_messageable, resolve_guild_id

log = logging.getLogger(__name__)


class SetupCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="setup", description="Legt fest, in welchen Kanal die Treffer kommen."
    )
    @app_commands.describe(
        channel="Zielkanal; ohne Angabe der aktuelle Kanal"
    )
    async def setup(
        self,
        interaction: discord.Interaction,
        channel: Optional[app_commands.AppCommandChannel] = None,
    ) -> None:
        try:
            guild_id = resolve_guild_id(interaction)
            target = channel.resolve() if channel is not None else interaction.channel
            if target is None:
                raise ValueError("Kein Kanal erkannt — bitte einen Textkanal angeben.")
            ensure_messageable(target)
        except (ValueError, PermissionError) as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        self.bot.store.set_channel(guild_id, target.id)
        log.info("Kanal fuer Guild %s auf %s gesetzt", guild_id, target.id)
        await interaction.response.send_message(
            f"Treffer landen ab jetzt in {target.mention}.", ephemeral=True
        )
