"""Tests for profile picture/banner commands, and embeds that show a user's avatar.

discord.py sets `.avatar`, `.guild_avatar`, `.banner` and `.guild_banner` to None when the user hasn't set one;
these tests cover each fallback.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from compass.cogs import gaming
from compass.cogs.main import Main
from compass.music.dataclasses import Song


def _asset(url: str) -> MagicMock:
    return MagicMock(url=url)


def _profile(*, avatar=None, guild_avatar=None, banner=None, guild_banner=None) -> MagicMock:
    m = MagicMock()
    m.mention = "<@1>"
    m.avatar = _asset(avatar) if avatar else None
    m.guild_avatar = _asset(guild_avatar) if guild_avatar else None
    m.default_avatar = _asset("default.png")
    m.banner = _asset(banner) if banner else None
    m.guild_banner = _asset(guild_banner) if guild_banner else None
    return m


@pytest.fixture
def cog(bot) -> Main:
    return Main(bot)


def _sent_embed(itx):
    return itx.followup.send.call_args.kwargs["embed"]


def test_profile_option_is_a_fixed_choice():
    # Free text let "server" (lowercase) silently fall into the wrong branch
    for command in (Main._avatar, Main._banner):
        (param,) = [p for p in command.parameters if p.name == "profile"]
        assert [c.value for c in param.choices] == ["User", "Server"]


##############
### avatar ###
##############


@pytest.mark.parametrize(
    "profile_kwargs, option, expected_url, note",
    [
        pytest.param({"avatar": "user.png"}, "User", "user.png", None, id="user avatar"),
        # Regression: .avatar is None for Discord's default avatar, and .url raised AttributeError
        pytest.param({}, "User", "default.png", None, id="default avatar"),
        pytest.param({"avatar": "user.png", "guild_avatar": "server.png"}, "Server", "server.png", None, id="server"),
        # Regression: .guild_avatar is None for most members
        pytest.param({"avatar": "user.png"}, "Server", "user.png", "no server avatar", id="no server avatar"),
    ],
)
async def test_avatar(cog, itx, profile_kwargs, option, expected_url, note):
    itx.guild.fetch_member = AsyncMock(return_value=_profile(**profile_kwargs))

    await cog._avatar.callback(cog, itx, None, option)

    embed = _sent_embed(itx)
    assert embed.image.url == expected_url
    if note:
        assert note in embed.description


##############
### banner ###
##############


async def test_banner_user(cog, itx, bot):
    bot.fetch_user = AsyncMock(return_value=_profile(banner="banner.png"))
    await cog._banner.callback(cog, itx, None, "User")
    assert _sent_embed(itx).image.url == "banner.png"


async def test_banner_none(cog, itx, bot):
    # Regression: .banner is None for most users, and .url raised AttributeError
    bot.fetch_user = AsyncMock(return_value=_profile())
    await cog._banner.callback(cog, itx, None, "User")
    assert "doesn't have a banner" in itx.followup.send.call_args.args[0]


async def test_banner_server(cog, itx, bot):
    itx.guild.fetch_member = AsyncMock(return_value=_profile(guild_banner="server-banner.png"))
    bot.fetch_user = AsyncMock()
    await cog._banner.callback(cog, itx, None, "Server")
    embed = _sent_embed(itx)
    assert embed.image.url == "server-banner.png"
    assert "server banner" in embed.description
    bot.fetch_user.assert_not_awaited()


async def test_banner_server_falls_back_to_user_banner(cog, itx, bot):
    itx.guild.fetch_member = AsyncMock(return_value=_profile())
    bot.fetch_user = AsyncMock(return_value=_profile(banner="banner.png"))
    await cog._banner.callback(cog, itx, None, "Server")
    embed = _sent_embed(itx)
    assert embed.image.url == "banner.png"
    assert "no server banner" in embed.description


###############################
### embeds showing avatars ###
###############################


def _default_avatar_user() -> MagicMock:
    u = MagicMock()
    u.avatar = None  # Discord's default avatar
    u.display_avatar.url = "default.png"
    u.name = u.mention = "user"
    return u


def test_now_playing_embed_with_default_avatar():
    # Regression: requested_by.avatar.url raised, so "Now Playing" was never sent for default-avatar users
    embed = Song(title="Song", requested_by=_default_avatar_user()).now_playing_embed()
    assert embed.footer.icon_url == "default.png"


async def test_lfg_post_with_default_avatar(itx, bot, monkeypatch):
    # Regression: itx.user.avatar.url raised, so default-avatar users couldn't create an LFG post
    monkeypatch.setattr(gaming.asyncio, "sleep", AsyncMock())  # the post's 1-hour cleanup
    cog = gaming.Gaming(bot)
    bot.db.update_channel_lfg(itx.guild.id, itx.channel.id)
    itx.user = _default_avatar_user()
    itx.user.id = 1  # stored in the LFG document
    itx.channel.send = AsyncMock(return_value=MagicMock(id=123))

    await cog._lfg.callback(cog, itx, 3, "Raid")

    embed = itx.channel.send.call_args.kwargs["embed"]
    assert embed.footer.icon_url == "default.png"
