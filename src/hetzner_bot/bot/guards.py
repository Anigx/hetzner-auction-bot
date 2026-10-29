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
