from decimal import Decimal

from hetzner_bot.bot.texts import describe_filter, guild_count_warning
from hetzner_bot.domain import Criteria, FilterRecord


def test_describe_filter_lists_criteria():
    rec = FilterRecord(
        id=1,
        guild_id=1,
        user_id=2,
        name="standard",
        criteria=Criteria(max_price=Decimal("45"), min_ram=64),
        mention=True,
        active=True,
    )
    text = describe_filter(rec, 3)
    assert "standard" in text
    assert "45" in text
    assert "64 GB" in text
    assert "3 passende Server" in text
    assert "Ping an" in text


def test_describe_filter_marks_paused():
    rec = FilterRecord(
        id=1,
        guild_id=1,
        user_id=2,
        name="x",
        criteria=Criteria(min_ram=64),
        mention=False,
        active=False,
    )
    assert "pausiert" in describe_filter(rec, 0)


def test_guild_count_warning_names_the_missing_scope():
    assert guild_count_warning(3) is None
    text = guild_count_warning(0)
    assert "bot" in text
    assert "applications.commands" in text
