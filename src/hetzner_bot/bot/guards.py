"""Rechteprüfungen für Slash-Commands."""

from __future__ import annotations

import discord


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


def ensure_messageable(channel) -> None:
    """Prüft, ob in den Kanal wirklich gepostet werden kann."""
    if getattr(channel, "type", None) is discord.ChannelType.category:
        raise ValueError(
            "Das ist eine Kategorie, kein Kanal. Bitte einen Textkanal waehlen, "
            "z.B. `/setup channel:#deals`."
        )
    if not hasattr(channel, "send"):
        raise ValueError("In diesen Kanal kann der Bot keine Nachrichten schreiben.")
