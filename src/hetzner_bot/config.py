"""Konfiguration aus Umgebungsvariablen."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

AUCTION_URL = "https://www.hetzner.com/_resources/app/data/app/live_data_sb.json"
DEFAULT_DATABASE_PATH = Path("data/bot.sqlite3")


class ConfigError(RuntimeError):
    """Ungültige oder fehlende Konfiguration."""


@dataclass(frozen=True)
class Config:
    discord_token: str
    database_path: Path
    auction_url: str
    poll_minutes: int
    max_posts_per_run: int
    max_filters_per_user: int
    log_level: str
    guild_id: int | None = None
    vat_percent: float = 0.0


def _positive_int(env: Mapping[str, str], key: str, default: int) -> int:
    raw = env.get(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(f"{key} muss eine ganze Zahl sein, war: {raw!r}") from None
    if value <= 0:
        raise ConfigError(f"{key} muss größer als 0 sein, war: {value}")
    return value


def _optional_int(env: Mapping[str, str], key: str) -> int | None:
    raw = (env.get(key) or "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(f"{key} muss eine ganze Zahl sein, war: {raw!r}") from None
    if value <= 0:
        raise ConfigError(f"{key} muss groesser als 0 sein, war: {value}")
    return value


def _percent(env: Mapping[str, str], key: str, default: float = 0.0) -> float:
    raw = (env.get(key) or "").strip()
    if not raw:
        return default
    try:
        value = float(raw.replace(",", "."))
    except ValueError:
        raise ConfigError(f"{key} muss eine Zahl sein, war: {raw!r}") from None
    if not 0 <= value <= 100:
        raise ConfigError(f"{key} muss zwischen 0 und 100 liegen, war: {value}")
    return value


def load_config(env: Mapping[str, str] | None = None) -> Config:
    values = os.environ if env is None else env

    token = (values.get("DISCORD_TOKEN") or "").strip()
    if not token:
        raise ConfigError("DISCORD_TOKEN fehlt")

    database_path = Path(values.get("DATABASE_PATH") or DEFAULT_DATABASE_PATH)
    auction_url = (values.get("AUCTION_URL") or AUCTION_URL).strip()
    log_level = (values.get("LOG_LEVEL") or "INFO").strip().upper()

    return Config(
        discord_token=token,
        database_path=database_path,
        auction_url=auction_url,
        poll_minutes=_positive_int(values, "POLL_MINUTES", 10),
        max_posts_per_run=_positive_int(values, "MAX_POSTS_PER_RUN", 15),
        max_filters_per_user=_positive_int(values, "MAX_FILTERS_PER_USER", 5),
        log_level=log_level,
        guild_id=_optional_int(values, "GUILD_ID"),
        vat_percent=_percent(values, "VAT_PERCENT"),
    )
