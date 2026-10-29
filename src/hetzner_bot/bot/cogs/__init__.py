"""Alle Slash-Command-Cogs."""

from hetzner_bot.bot.cogs.manage import ManageCog
from hetzner_bot.bot.cogs.setup import SetupCog
from hetzner_bot.bot.cogs.watch import WatchCog

ALL_COGS = (SetupCog, WatchCog, ManageCog)

__all__ = ["ALL_COGS", "ManageCog", "SetupCog", "WatchCog"]
