from pathlib import Path

import pytest

from hetzner_bot.config import ConfigError, load_config


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


def test_filter_limit_has_default_and_can_be_changed():
    assert load_config({"DISCORD_TOKEN": "abc"}).max_filters_per_user == 5
    cfg = load_config({"DISCORD_TOKEN": "abc", "MAX_FILTERS_PER_USER": "3"})
    assert cfg.max_filters_per_user == 3


def test_guild_id_is_optional():
    assert load_config({"DISCORD_TOKEN": "abc"}).guild_id is None
    assert load_config({"DISCORD_TOKEN": "abc", "GUILD_ID": "123"}).guild_id == 123


def test_config_rejects_non_numeric_guild_id():
    with pytest.raises(ConfigError):
        load_config({"DISCORD_TOKEN": "abc", "GUILD_ID": "dev"})
