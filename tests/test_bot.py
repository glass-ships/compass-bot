"""Tests for CompassBot helpers that can be called without starting the bot."""

from unittest.mock import MagicMock

import pytest

from compass.bot import CompassBot
from compass.config.bot_config import DEFAULT_PREFIX
from tests.conftest import GUILD_ID

BOT_USER_ID = 4242
MENTIONS = [f"<@{BOT_USER_ID}> ", f"<@!{BOT_USER_ID}> "]


@pytest.fixture
def compass(bot) -> MagicMock:
    """Stands in for `self` and the `bot` argument: only `.db` and `.user.id` are used."""
    bot.user.id = BOT_USER_ID
    return bot


def _msg(guild) -> MagicMock:
    m = MagicMock()
    m.guild = guild
    return m


async def test_get_prefix_in_dm_uses_default(compass):
    # Regression: logged msg.guild.name before the guild check, so every DM raised AttributeError
    compass.db = MagicMock()
    assert await CompassBot._get_prefix(compass, compass, _msg(None)) == [*MENTIONS, DEFAULT_PREFIX]
    compass.db.get_prefix.assert_not_called()


async def test_get_prefix_uses_guild_prefix(compass, guild):
    compass.db.update_prefix(GUILD_ID, "!")
    assert await CompassBot._get_prefix(compass, compass, _msg(guild)) == [*MENTIONS, "!"]


async def test_get_prefix_sets_default_when_unset(compass, guild):
    compass.db.drop_field(GUILD_ID, "prefix")
    assert await CompassBot._get_prefix(compass, compass, _msg(guild)) == [*MENTIONS, DEFAULT_PREFIX]
    assert compass.db.get_prefix(GUILD_ID) == DEFAULT_PREFIX
