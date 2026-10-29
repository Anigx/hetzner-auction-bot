"""Start des Hetzner-Auktions-Bots."""

from __future__ import annotations

import logging
from typing import Any

import discord
import httpx
from discord.ext import commands
from dotenv import load_dotenv

from cogs.commands import Commands
from config import Config, load_config
from hetzner.models import Server
from store import Store

log = logging.getLogger("hetzner_bot")

_USER_AGENT = "hetzner-auction-discord-bot/0.1 (+https://www.hetzner.com/sb/)"


class HetznerBot(commands.Bot):
    def __init__(self, config: Config) -> None:
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        self.config = config
        self.store = Store(config.database_path)
        self.http: httpx.AsyncClient | None = None
        self.last_servers: list[Server] = []
        self.poller: Any = None

    async def setup_hook(self) -> None:
        self.store.init_schema()
        self.http = httpx.AsyncClient(
            timeout=10.0,
            headers={"User-Agent": _USER_AGENT},
        )
        await self.add_cog(Commands(self))

    async def on_ready(self) -> None:
        await self.tree.sync()
        log.info("Eingeloggt als %s", self.user)

    async def close(self) -> None:
        if self.http is not None:
            await self.http.aclose()
        self.store.close()
        await super().close()


def main() -> None:
    load_dotenv()
    config = load_config()
    logging.basicConfig(
        level=config.log_level,
        format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
    )
    HetznerBot(config).run(config.discord_token)


if __name__ == "__main__":
    main()
