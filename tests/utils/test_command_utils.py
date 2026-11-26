"""Tests for compass.utils.command_utils (Discord helpers, using fake Discord objects)."""

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from compass.utils.command_utils import (
    EMBED_DESC_LIMIT,
    get_emojis,
    move_message,
    paginate,
    send_embed,
    send_embed_long,
)


def _emoji(name: str, animated: bool) -> MagicMock:
    e = MagicMock()
    e.name = name
    e.animated = animated
    return e


def test_get_emojis_splits_static_and_animated(guild):
    static, anim = _emoji("smile", False), _emoji("dance", True)
    guild.emojis = [static, anim]
    assert get_emojis(guild) == ([static], [anim])


async def test_send_embed():
    channel = MagicMock(send=AsyncMock())
    await send_embed(channel=channel, title="Hi", description="desc", footer="foot")

    embed = channel.send.call_args.kwargs["embed"]
    assert isinstance(embed, discord.Embed)
    assert embed.title == "Hi"
    assert embed.description == "desc"
    assert embed.footer.text == "foot"


async def test_send_embed_long_short_message_sends_once():
    channel = MagicMock(send=AsyncMock())
    await send_embed_long(channel=channel, title="T", description="short")
    channel.send.assert_awaited_once()


async def test_send_embed_long_splits_long_message():
    channel = MagicMock(send=AsyncMock())
    await send_embed_long(channel=channel, title="T", description="x" * 9000)

    assert channel.send.await_count == 3
    titles = [c.kwargs["embed"].title for c in channel.send.await_args_list]
    assert titles == ["T (Page 1/3)", "T (Page 2/3)", "T (Page 3/3)"]


def _sent(channel) -> list[discord.Embed]:
    return [c.kwargs["embed"] for c in channel.send.await_args_list]


async def test_send_embed_long_pages_fit_discord_limit():
    # Regression: "\n".join(str_chunk) put a newline between every character, so pages exceeded 4096
    channel = MagicMock(send=AsyncMock())
    text = "x" * 9000
    await send_embed_long(channel=channel, title="T", description=text)

    pages = [e.description for e in _sent(channel)]
    assert all(len(p) <= EMBED_DESC_LIMIT for p in pages)
    assert "".join(pages) == text


async def test_send_embed_long_page_count_matches_pages_sent():
    # Regression: 4001 chars produced 3 chunks titled "Page 3/2"
    channel = MagicMock(send=AsyncMock())
    await send_embed_long(channel=channel, title="T", description="x" * (EMBED_DESC_LIMIT + 1))
    assert [e.title for e in _sent(channel)] == ["T (Page 1/2)", "T (Page 2/2)"]


async def test_send_embed_long_breaks_on_lines():
    channel = MagicMock(send=AsyncMock())
    lines = [f"/command_{i:04d}" for i in range(500)]  # ~7500 chars
    await send_embed_long(channel=channel, description="\n".join(lines))

    pages = [e.description for e in _sent(channel)]
    assert len(pages) == 2
    assert [line for p in pages for line in p.splitlines()] == lines  # no line split across pages


async def test_send_embed_long_accepts_list():
    # Regression: a list was measured by item count and passed raw to Embed(description=list)
    channel = MagicMock(send=AsyncMock())
    lines = ["y" * 200] * 50  # 50 items, ~10k chars
    await send_embed_long(channel=channel, description=lines)

    pages = [e.description for e in _sent(channel)]
    assert len(pages) == 3
    assert all(len(p) <= EMBED_DESC_LIMIT for p in pages)
    assert "\n".join(pages).splitlines() == lines


async def test_send_embed_long_no_title():
    channel = MagicMock(send=AsyncMock())
    await send_embed_long(channel=channel, description="x" * 5000)
    assert [e.title for e in _sent(channel)] == ["(Page 1/2)", "(Page 2/2)"]


async def test_send_embed_long_extras_placement():
    channel = MagicMock(send=AsyncMock())
    await send_embed_long(
        channel=channel,
        description="x" * 5000,
        image="https://img",
        thumbnail="https://thumb",
        footer="foot",
    )
    first, last = _sent(channel)
    assert first.thumbnail.url == "https://thumb"
    assert last.thumbnail.url is None
    assert last.image.url == "https://img" and first.image.url is None
    assert last.footer.text == "foot" and first.footer.text is None
    assert first.color == last.color


async def test_send_embed_long_empty_still_sends():
    channel = MagicMock(send=AsyncMock())
    await send_embed_long(channel=channel, title="Empty")
    (embed,) = _sent(channel)
    assert embed.title == "Empty"
    assert embed.description is None


@pytest.mark.parametrize(
    "text, expected",
    [
        pytest.param("", [], id="empty"),
        pytest.param("a\nb", ["a\nb"], id="fits"),
        pytest.param("aaa\nbbb", ["aaa", "bbb"], id="breaks on newline"),
        pytest.param("aaaaaaa", ["aaaaa", "aa"], id="hard-splits long line"),
        pytest.param("ab\naaaaaaa\ncd", ["ab", "aaaaa", "aa\ncd"], id="long line between short ones"),
        pytest.param("ab\naaaaaaa\ncdef", ["ab", "aaaaa", "aa", "cdef"], id="long-line tail too big to merge"),
    ],
)
def test_paginate(text, expected):
    assert paginate(text, limit=5) == expected


async def test_move_message_rejects_non_text_channel(itx):
    itx.channel = MagicMock()  # not a TextChannel/Thread
    await move_message(itx, MagicMock(), "123")

    itx.response.defer.assert_awaited_once_with(ephemeral=True)
    assert "Unable to move" in itx.followup.send.call_args.args[0]


async def test_move_message_reposts_and_deletes(itx):
    original = MagicMock()
    original.content = "hello"
    original.author.mention = "<@1>"
    original.channel.id = 3000
    original.attachments = []
    original.delete = AsyncMock()

    itx.channel = MagicMock(spec=discord.TextChannel)
    itx.channel.fetch_message = AsyncMock(return_value=original)
    target = MagicMock()
    target.send = AsyncMock(return_value=MagicMock(jump_url="https://discord.com/x"))

    await move_message(itx, target, "3000-456")  # "channel-message" id format is accepted

    itx.channel.fetch_message.assert_awaited_once_with(456)
    assert "hello" in target.send.call_args.kwargs["content"]
    original.delete.assert_awaited_once()
    assert "https://discord.com/x" in itx.followup.send.call_args.args[0]
