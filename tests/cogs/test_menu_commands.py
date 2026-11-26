"""Tests for the "Move Message" context menu and its channel picker."""

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import discord
import pytest

from compass.cogs import menu_commands
from compass.cogs.menu_commands import MenuCommands, SelectMenuChannel


@pytest.fixture
def cog(bot) -> MenuCommands:
    return MenuCommands(bot)


@pytest.fixture
def fake_move(monkeypatch) -> AsyncMock:
    move = AsyncMock()
    monkeypatch.setattr(menu_commands, "move_message", move)
    return move


def _pick(channel_id: int):
    """Simulate the user choosing a channel (ChannelSelect.values holds partial channels)."""
    return patch.object(SelectMenuChannel, "values", new_callable=PropertyMock, return_value=[MagicMock(id=channel_id)])


async def test_move_message_sends_native_channel_picker(cog, itx, guild):
    # Regression: built one SelectOption per text channel; Discord rejects more than 25 (and topics > 100 chars)
    guild.text_channels = [MagicMock(name=f"c{i}", id=i, topic="x" * 200) for i in range(30)]
    msg = MagicMock(id=555, guild=guild)

    await cog._move_message(itx, msg)

    itx.response.defer.assert_awaited_once_with(ephemeral=True)
    (select,) = itx.followup.send.call_args.kwargs["view"].children
    assert isinstance(select, discord.ui.ChannelSelect)
    assert select.message_id == 555
    assert discord.ChannelType.public_thread in select.channel_types


async def test_picking_a_channel_moves_the_message(itx, guild, fake_move):
    target = MagicMock()
    guild.get_channel_or_thread = MagicMock(return_value=target)
    select = SelectMenuChannel(message_id=555)

    with _pick(42):
        await select.callback(itx)

    guild.get_channel_or_thread.assert_called_once_with(42)
    fake_move.assert_awaited_once_with(itx, target, "555")


async def test_picking_a_missing_channel_replies(itx, guild, fake_move):
    # Regression: replied with followup.send to an interaction that had no response yet
    guild.get_channel_or_thread = MagicMock(return_value=None)
    select = SelectMenuChannel(message_id=555)

    with _pick(42):
        await select.callback(itx)

    itx.response.send_message.assert_awaited_once_with("Channel not found.", ephemeral=True)
    fake_move.assert_not_awaited()


async def test_move_error_is_reported_and_reraised(itx, guild, fake_move):
    guild.get_channel_or_thread = MagicMock(return_value=MagicMock())
    fake_move.side_effect = RuntimeError("boom")
    select = SelectMenuChannel(message_id=555)

    with _pick(42), pytest.raises(RuntimeError):
        await select.callback(itx)

    assert "boom" in itx.followup.send.call_args.args[0]
