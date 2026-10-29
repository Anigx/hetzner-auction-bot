"""Slash-Commands des Bots."""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)


def resolve_guild_id(interaction: discord.Interaction) -> int:
    """Liefert die Guild-ID oder wirft, wenn der Command ausserhalb eines Servers läuft
    oder die Person keine Server-verwalten-Rechte hat."""
    guild = getattr(interaction, "guild", None)
    if guild is None:
        raise ValueError("Dieser Command funktioniert nur auf einem Discord-Server.")

    permissions = getattr(getattr(interaction, "user", None), "guild_permissions", None)
    if permissions is None or not permissions.manage_guild:
        raise PermissionError("Dafuer brauchst du das Recht 'Server verwalten'.")

    return int(guild.id)


class Commands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="setup", description="Legt fest, in welchen Kanal die Treffer kommen.")
    @app_commands.describe(channel="Kanal fuer Treffer aus der Serverboerse")
    async def setup(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        try:
            guild_id = resolve_guild_id(interaction)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        except PermissionError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        self.bot.store.set_channel(guild_id, channel.id)
        log.info("Kanal fuer Guild %s auf %s gesetzt", guild_id, channel.id)
        await interaction.response.send_message(
            f"Treffer landen ab jetzt in {channel.mention}.", ephemeral=True
        )
