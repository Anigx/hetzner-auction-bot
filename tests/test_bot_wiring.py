import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from hetzner_bot.bot.app import HetznerBot
from hetzner_bot.config import Config


def build_config(tmp_path) -> Config:
    return Config(
        discord_token="test",
        database_path=tmp_path / "db.sqlite3",
        auction_url="https://example.invalid/sb.json",
        poll_minutes=10,
        max_posts_per_run=15,
        max_filters_per_user=5,
        log_level="INFO",
    )


def test_bot_does_not_clobber_discords_http_client(tmp_path):
    """discord.py legt in Client.__init__ self.http an; ein eigenes Attribut mit
    diesem Namen macht den Login unmoeglich ('NoneType' has no attribute 'loop')."""
    bot = HetznerBot(build_config(tmp_path))

    assert isinstance(bot.http, discord.http.HTTPClient)
    assert bot.auction_http is None


@pytest.mark.asyncio
async def test_bot_setup_hook_runs_without_network(tmp_path):
    """Der Start scheiterte im Container an der Client-Initialisierung, nicht am Code
    danach. Dieser Test fuehrt den echten Setup-Pfad aus."""
    bot = HetznerBot(build_config(tmp_path))

    await bot._async_setup_hook()
    await bot.setup_hook()

    assert bot.poller is not None
    assert bot.auction_http is not None
    assert bot.cogs, "keine Cog geladen"
    await bot.close()


@pytest.mark.asyncio
async def test_all_commands_are_registered(tmp_path):
    """Faengt Annotationsfehler (z.B. Optional[AppCommandChannel]) beim Registrieren."""
    bot = HetznerBot(build_config(tmp_path))
    await bot._async_setup_hook()
    await bot.setup_hook()

    names = {command.name for command in bot.tree.get_commands()}
    assert {
        "setup",
        "watch",
        "filters",
        "unwatch",
        "pause",
        "resume",
        "status",
        "help",
        "matches",
    } <= names

    setup = bot.tree.get_command("setup")
    params = {param.name: param for param in setup.parameters}
    assert "channel" in params
    assert params["channel"].required is False

    await bot.close()


@pytest.mark.asyncio
async def test_on_ready_warns_when_bot_is_in_no_guild(tmp_path, caplog):
    """Der Startpfad lief im Container durch, erst on_ready warf einen NameError."""
    bot = HetznerBot(build_config(tmp_path))
    await bot._async_setup_hook()
    await bot.setup_hook()

    bot.tree.sync = AsyncMock()
    bot.poll_loop = SimpleNamespace(is_running=lambda: True, cancel=lambda: None)

    with caplog.at_level(logging.WARNING):
        await bot.on_ready()

    assert any("keinem Server" in record.message for record in caplog.records)
    await bot.close()
