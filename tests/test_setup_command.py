import discord
import pytest

from hetzner_bot.bot.guards import ensure_messageable, resolve_guild_id


class FakeGuild:
    id = 42


class FakeInteraction:
    def __init__(self, guild, user_permissions):
        self.guild = guild
        self.user = type("U", (), {"guild_permissions": user_permissions})()


def test_missing_guild_is_rejected():
    with pytest.raises(ValueError):
        resolve_guild_id(FakeInteraction(None, None))


def test_guild_without_permission_is_rejected():
    perms = type("P", (), {"manage_guild": False})()
    with pytest.raises(PermissionError):
        resolve_guild_id(FakeInteraction(FakeGuild(), perms))


def test_guild_with_permission_is_accepted():
    perms = type("P", (), {"manage_guild": True})()
    assert resolve_guild_id(FakeInteraction(FakeGuild(), perms)) == 42


def test_category_is_rejected_with_helpful_message():
    category = type("C", (), {"type": discord.ChannelType.category})()
    with pytest.raises(ValueError) as excinfo:
        ensure_messageable(category)
    assert "Kategorie" in str(excinfo.value)


def test_channel_without_send_is_rejected():
    with pytest.raises(ValueError):
        ensure_messageable(type("X", (), {"type": discord.ChannelType.voice})())


def test_text_channel_is_accepted():
    channel = type(
        "T", (), {"type": discord.ChannelType.text, "send": lambda self, **kw: None}
    )()
    ensure_messageable(channel)
