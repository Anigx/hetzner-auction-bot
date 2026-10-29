from pathlib import Path

import pytest

from config import ConfigError, load_config


def test_load_config_uses_defaults():
    cfg = load_config({"DISCORD_TOKEN": "abc"})
    assert cfg.poll_minutes == 10
    assert cfg.max_posts_per_run == 15
    assert cfg.database_path == Path("data/bot.sqlite3")
    assert cfg.auction_url.endswith("live_data_sb.json")


def test_load_config_requires_token():
    with pytest.raises(ConfigError):
        load_config({})


def test_load_config_rejects_non_positive_interval():
    with pytest.raises(ConfigError):
        load_config({"DISCORD_TOKEN": "abc", "POLL_MINUTES": "0"})
