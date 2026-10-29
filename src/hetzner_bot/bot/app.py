"""Der Bot: Kompositionswurzel, Poll-Loop, Einstiegspunkt."""

from __future__ import annotations

import logging

import discord
import httpx
from discord.ext import commands, tasks
from dotenv import load_dotenv

from hetzner_bot.auction import fetch_servers
from hetzner_bot.bot.cogs import ALL_COGS
from hetzner_bot.config import Config, load_config
from hetzner_bot.domain import Server
from hetzner_bot.engine import Poller
from hetzner_bot.storage import Store

log = logging.getLogger("hetzner_bot")

USER_AGENT = "hetzner-auction-discord-bot/0.1 (+https://www.hetzner.com/sb/)"


class HetznerBot(commands.Bot):
    def __init__(self, config: Config) -> None:
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        self.config = config
        self.store = Store(config.database_path)
        self.http: httpx.AsyncClient | None = None
        self.last_servers: list[Server] = []
        self.last_poll_at = None
        self.last_error: str | None = None
        self.poller: Poller | None = None

    async def setup_hook(self) -> None:
        self.store.init_schema()
        self.http = httpx.AsyncClient(timeout=10.0, headers={"User-Agent": USER_AGENT})
        self.poller = Poller(self, self.store, self.config)
        self.poll_loop.change_interval(minutes=self.config.poll_minutes)
        for cog in ALL_COGS:
            await self.add_cog(cog(self))

    async def on_ready(self) -> None:
        await self.tree.sync()
        log.info("Eingeloggt als %s", self.user)
        if not self.poll_loop.is_running():
            self.poll_loop.start()

    async def current_servers(self) -> list[Server]:
        """Snapshot aus dem letzten Poll; holt einmal frisch, wenn noch keiner da ist."""
        if self.last_servers:
            return self.last_servers
        assert self.http is not None
        self.last_servers = await fetch_servers(self.http, self.config.auction_url)
        return self.last_servers

    @tasks.loop(minutes=10)
    async def poll_loop(self) -> None:
        assert self.poller is not None
        report = await self.poller.run_once()
        log.info(
            "Poll: %s Server, %s gepostet, %s wartend, fehlgeschlagen=%s",
            report.fetched,
            report.posted,
            report.queued,
            report.failed,
        )

    async def close(self) -> None:
        self.poll_loop.cancel()
        if self.http is not None:
            await self.http.aclose()
        self.store.close()
        await super().close()


def main() -> None:
    load_dotenv()
    config = load_config()
    logging.basicConfig(
        level=config.log_level,
        format=(
            '{"time":"%(asctime)s","level":"%(levelname)s",'
            '"logger":"%(name)s","msg":"%(message)s"}'
        ),
    )
    HetznerBot(config).run(config.discord_token)
