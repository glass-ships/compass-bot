"""Tests for the Gaming cog's LFG buttons.

Button callbacks are called through the view instance: `await view.join_lfg.callback(itx)`.
`update_lfg_join` / `update_lfg_leave` are stubbed (mongomock may not support their `$expr` filter; they have their
own tests in tests/test_database.py), so these tests cover the view's logic and its interaction responses.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from compass.cogs.gaming import Gaming, LFGView

LFG_ID = 777
LEADER_ID = 100
USER_ID = 1  # the conftest `member` fixture, i.e. itx.user


@pytest.fixture
def cog(bot) -> Gaming:
    bot.add_view = MagicMock()
    return Gaming(bot)


@pytest.fixture
async def view(cog) -> LFGView:  # noqa: ARG001 - async: a View needs a running loop; `cog` sets `global bot`
    return LFGView()


@pytest.fixture
def post(itx, bot) -> dict:
    """An active LFG post for 2 players, and itx pointing at its message."""
    bot.db.add_lfg(lfg_id=LFG_ID, leader_id=LEADER_ID, num_players=2)
    itx.message.id = LFG_ID
    itx.message.add_reaction = AsyncMock()
    leader = MagicMock(display_name="Leader")
    itx.guild.get_member = MagicMock(return_value=leader)
    bot.db.update_lfg_join = MagicMock(return_value=True)
    bot.db.update_lfg_leave = MagicMock(return_value=True)
    return bot.db.get_lfg(LFG_ID)


def _replied(itx) -> str:
    """The ephemeral reply to the click (content or embed title)."""
    itx.response.send_message.assert_awaited_once()
    call = itx.response.send_message.call_args
    assert call.kwargs["ephemeral"] is True
    return call.args[0] or call.kwargs["embed"].title


async def test_view_is_persistent(view):
    # Regression: the default 180s timeout killed the buttons 3 minutes into an hour-long post
    assert view.timeout is None
    assert all(item.custom_id for item in view.children)  # required for bot.add_view


async def test_cog_load_registers_view(cog, bot):
    await cog.cog_load()
    (registered,) = bot.add_view.call_args.args
    assert isinstance(registered, LFGView)


@pytest.mark.parametrize("button", ["view_roster", "join_lfg", "leave_lfg"])
async def test_expired_post_replies(view, itx, button):
    # Regression: view_roster read lfg["leader"] before the None check (TypeError); join/leave never responded
    itx.message.id = 999  # no such LFG
    await getattr(view, button).callback(itx)
    assert _replied(itx) == "Inactive Post"


@pytest.mark.usefixtures("post")
async def test_view_roster(view, itx, bot):
    bot.db.lfg_collection.update_one({"lfg_id": LFG_ID}, {"$set": {"joined": [5, 6]}})

    await view.view_roster.callback(itx)

    assert _replied(itx) == "Leader's LFG"
    fireteam = itx.response.send_message.call_args.kwargs["embed"].fields[0].value
    assert fireteam == f"<@{LEADER_ID}>\n<@5>\n<@6>"


@pytest.mark.usefixtures("post")
async def test_join_replies_and_pings_leader(view, itx, bot):
    await view.join_lfg.callback(itx)

    bot.db.update_lfg_join.assert_called_once_with(lfg_id=LFG_ID, user_id=USER_ID)
    assert _replied(itx) == "You've joined the fireteam."
    # Regression: pinged itx.message.author (the bot) instead of the LFG leader
    assert itx.channel.send.call_args.kwargs["content"] == f"<@{LEADER_ID}>"


@pytest.mark.usefixtures("post")
async def test_join_last_spot_adds_full_reaction(view, itx, bot):
    bot.db.lfg_collection.update_one({"lfg_id": LFG_ID}, {"$set": {"joined": [5]}})
    await view.join_lfg.callback(itx)
    itx.message.add_reaction.assert_awaited_once_with("🇫")


@pytest.mark.parametrize(
    "setup, expected",
    [
        pytest.param({"leader": USER_ID}, "You cannot join your own LFG post.", id="leader"),
        pytest.param({"joined": [USER_ID]}, "You are already in the fireteam", id="already joined"),
    ],
)
@pytest.mark.usefixtures("post")
async def test_join_refusals(view, itx, bot, setup, expected):
    bot.db.lfg_collection.update_one({"lfg_id": LFG_ID}, {"$set": setup})
    await view.join_lfg.callback(itx)
    assert _replied(itx).startswith(expected)
    bot.db.update_lfg_join.assert_not_called()
    itx.channel.send.assert_not_awaited()


@pytest.mark.usefixtures("post")
async def test_join_when_db_refuses(view, itx, bot):
    bot.db.update_lfg_join.return_value = False
    await view.join_lfg.callback(itx)
    assert _replied(itx).startswith("Unable to join")
    itx.channel.send.assert_not_awaited()


@pytest.mark.usefixtures("post")
async def test_leave_replies_and_pings_leader(view, itx, bot):
    bot.db.lfg_collection.update_one({"lfg_id": LFG_ID}, {"$set": {"joined": [USER_ID]}})
    await view.leave_lfg.callback(itx)

    bot.db.update_lfg_leave.assert_called_once_with(lfg_id=LFG_ID, user_id=USER_ID)
    assert _replied(itx) == "You've left the fireteam."
    assert itx.channel.send.call_args.kwargs["content"] == f"<@{LEADER_ID}>"


@pytest.mark.parametrize(
    "setup, expected",
    [
        pytest.param({"leader": USER_ID}, "You cannot leave your own LFG post.", id="leader"),
        pytest.param({}, "You are not in the fireteam", id="not in it"),
    ],
)
@pytest.mark.usefixtures("post")
async def test_leave_refusals(view, itx, bot, setup, expected):
    if setup:
        bot.db.lfg_collection.update_one({"lfg_id": LFG_ID}, {"$set": setup})
    await view.leave_lfg.callback(itx)
    assert _replied(itx).startswith(expected)
    bot.db.update_lfg_leave.assert_not_called()
