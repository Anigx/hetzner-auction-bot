import pytest

from cogs.commands import resolve_guild_id


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
