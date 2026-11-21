"""Tests for the Listeners cog (event handlers).

Listeners are plain coroutine methods, so they're called directly: `await cog.on_member_remove(member)`.
"""

import inspect
import io
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import discord
import httpx
import pytest
from discord.ext import commands
from PIL import Image

from compass.cogs import listeners
from compass.cogs.listeners import Listeners
from compass.config.bot_config import SERVERS
from tests.conftest import GUILD_ID, MOD_ROLE_ID, make_member, make_role

LOGS_CHANNEL_ID = 4000
VIDS_CHANNEL_ID = 5000
WELCOME_CHANNEL_ID = 6000


@pytest.fixture
def cog(bot) -> Listeners:
    return Listeners(bot)


def make_channel(channel_id: int) -> MagicMock:
    channel = MagicMock()
    channel.id = channel_id
    channel.send = AsyncMock(return_value=MagicMock(jump_url=f"https://discord.com/channels/x/{channel_id}/1"))
    return channel


def make_message(guild, content: str = "", author=None, attachments=None, channel_id: int = 3000) -> MagicMock:
    msg = MagicMock()
    msg.id = 777
    msg.guild = guild
    msg.content = content
    msg.author = author or make_member(user_id=1, name="regular")
    msg.author.bot = False
    msg.attachments = list(attachments or [])
    msg.channel = make_channel(channel_id)
    msg.created_at = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
    msg.delete = AsyncMock()
    msg.add_reaction = AsyncMock()
    msg.remove_reaction = AsyncMock()
    return msg


def make_attachment(filename: str, content_type: str | None, size: int) -> MagicMock:
    a = MagicMock()
    a.filename = filename
    a.content_type = content_type
    a.size = size
    return a


########################
### on_command_error ###
########################


def _invoke_error() -> commands.CommandInvokeError:
    """A CommandInvokeError chained from a ValueError, as discord.py raises it."""
    try:
        try:
            raise ValueError("boom")
        except ValueError as e:
            raise commands.CommandInvokeError(e) from e
    except commands.CommandInvokeError as err:
        return err


async def test_command_not_found_is_silent(cog, ctx):
    await cog.on_command_error(ctx, commands.CommandNotFound("nope"))
    ctx.send.assert_not_awaited()


@pytest.mark.parametrize(
    "error, expected",
    [
        (commands.CommandOnCooldown(commands.Cooldown(1, 10), 3.14159, commands.BucketType.user), "after 3.1 seconds"),
        (commands.MissingPermissions(["ban_members"]), "missing the required permissions"),
        (
            commands.MissingRequiredArgument(commands.Parameter("arg", inspect.Parameter.POSITIONAL_OR_KEYWORD)),
            "Missing a required argument: arg",
        ),
        (commands.BadArgument("bad"), "Something about your input was wrong"),  # UserInputError subclass
    ],
)
async def test_command_error_messages(cog, ctx, error, expected):
    await cog.on_command_error(ctx, error)
    assert expected in ctx.send.call_args.kwargs["embed"].description


async def test_unexpected_error_shows_original_traceback_only(cog, ctx):
    ctx.message.content = ";broken"
    await cog.on_command_error(ctx, _invoke_error())

    description = ctx.send.call_args.kwargs["embed"].description
    assert "Something went wrong" in description
    assert ";broken" in description
    assert "ValueError: boom" in description
    assert "CommandInvokeError" not in description  # cut at "The above exception was the direct cause..."


@pytest.mark.xfail(
    reason="BUG: CheckFailure leaves message empty but still sends an embed with an empty description "
    "(the mod checks already sent their own reply; Discord rejects empty embeds)",
    strict=True,
)
async def test_check_failure_sends_nothing(cog, ctx):
    await cog.on_command_error(ctx, commands.CheckFailure())
    ctx.send.assert_not_awaited()


###################
### move_videos ###
###################


@pytest.fixture
def vids_channel(bot):
    """Configure a videos channel and make bot.fetch_channel return it."""
    bot.db.update_channel_vids(GUILD_ID, VIDS_CHANNEL_ID)
    channel = make_channel(VIDS_CHANNEL_ID)
    bot.fetch_channel = AsyncMock(return_value=channel)
    return channel


@pytest.fixture
def no_downloads(monkeypatch):
    """Stub out attachment downloads and discord.File (which would open the file)."""
    download = AsyncMock()
    monkeypatch.setattr(listeners, "download", download)
    monkeypatch.setattr(listeners.discord, "File", MagicMock(side_effect=lambda path: f"File({path})"))
    return download


@pytest.mark.usefixtures("vids_channel")
async def test_move_videos_ignores_bots(cog, guild, bot):
    msg = make_message(guild, "https://youtube.com/watch?v=1")
    msg.author.bot = True
    await cog.move_videos(msg)
    bot.fetch_channel.assert_not_awaited()


@pytest.mark.parametrize("unset", ["drop", 0], ids=["field missing (None)", "zero"])
async def test_move_videos_no_channel_configured(cog, guild, bot, unset):
    # Regression: 0 (the guild-data default for "unset") used to reach bot.fetch_channel(0)
    if unset == "drop":
        bot.db.drop_field(GUILD_ID, "chan_vids")
    else:
        bot.db.update_channel_vids(GUILD_ID, 0)
    bot.fetch_channel = AsyncMock()
    msg = make_message(guild, "https://youtube.com/watch?v=1")
    await cog.move_videos(msg)
    bot.fetch_channel.assert_not_awaited()
    msg.delete.assert_not_awaited()


@pytest.mark.usefixtures("vids_channel")
async def test_move_videos_already_in_video_channel(cog, guild):
    msg = make_message(guild, "https://youtube.com/watch?v=1", channel_id=VIDS_CHANNEL_ID)
    await cog.move_videos(msg)
    msg.delete.assert_not_awaited()


async def test_move_videos_ignores_non_video_messages(cog, guild, vids_channel):
    png = make_attachment("a.png", "image/png", 10)
    msg = make_message(guild, "just chatting https://example.com", attachments=[png])
    await cog.move_videos(msg)
    msg.delete.assert_not_awaited()
    vids_channel.send.assert_not_awaited()


@pytest.mark.parametrize(
    "content",
    [
        "https://youtube.com/watch?v=abc",
        "https://youtu.be/abc",
        "https://vimeo.com/123",
        "https://www.dailymotion.com/video/x1",
        "https://www.tiktok.com/@user/video/1",
    ],
)
async def test_move_videos_moves_video_links(cog, guild, vids_channel, content):
    msg = make_message(guild, f"look {content}")
    await cog.move_videos(msg)

    vids_channel.send.assert_awaited_once()
    assert content in vids_channel.send.call_args.kwargs["content"]
    msg.delete.assert_awaited_once()
    assert "was moved to" in msg.channel.send.call_args.args[0]


async def test_move_videos_moves_video_attachment(cog, guild, vids_channel, no_downloads):
    video = make_attachment("clip.mp4", "video/mp4", 1000)
    msg = make_message(guild, "", attachments=[video])
    await cog.move_videos(msg)

    no_downloads.assert_awaited_once_with(msg, video, "temp/moved_messages")
    files = vids_channel.send.call_args.kwargs["files"]
    assert files == ["File(downloads/Test Guild/temp/moved_messages/clip.mp4)"]
    msg.delete.assert_awaited_once()


async def test_move_videos_too_large_attachment_is_noted_not_downloaded(cog, guild, vids_channel, no_downloads):
    huge = make_attachment("huge.mp4", "video/mp4", guild.filesize_limit + 1)
    msg = make_message(guild, "", attachments=[huge])
    await cog.move_videos(msg)

    no_downloads.assert_not_awaited()
    assert "too large" in vids_channel.send.call_args.kwargs["content"]


@pytest.mark.usefixtures("vids_channel")
async def test_move_videos_attachment_without_content_type(cog, guild):
    # Regression: content_type can be None, and `"video" in None` raised TypeError
    msg = make_message(guild, "", attachments=[make_attachment("mystery", None, 10)])
    await cog.move_videos(msg)
    msg.delete.assert_not_awaited()


@pytest.mark.parametrize(
    "content_type, expected",
    [("video/mp4", True), ("video/quicktime", True), ("image/png", False), ("", False), (None, False)],
)
def test_is_video(content_type, expected):
    assert listeners.is_video(make_attachment("f", content_type, 10)) is expected


@pytest.mark.parametrize("listener", ["move_videos", "bat_react"])
async def test_on_message_listeners_ignore_dms(cog, listener):
    # Regression: on_message also fires for DMs, where msg.guild is None
    msg = make_message(None, "hello bats")
    await getattr(cog, listener)(msg)


####################
### log_activity ###
####################


async def test_log_activity_disabled_by_default(cog, guild, bot):
    msg = make_message(guild, "hi")
    await cog.log_activity(msg)
    assert bot.db.get_user_log(GUILD_ID, msg.author.id) is None


async def test_log_activity_records_message_time(cog, guild, bot):
    bot.db.add_or_update_field(GUILD_ID, "track_activity", True)
    msg = make_message(guild, "hi")
    await cog.log_activity(msg)
    assert bot.db.get_user_log(GUILD_ID, msg.author.id) == msg.created_at


async def test_log_activity_ignores_bots(cog, guild, bot):
    bot.db.add_or_update_field(GUILD_ID, "track_activity", True)
    msg = make_message(guild, "hi")
    msg.author.bot = True
    await cog.log_activity(msg)
    assert bot.db.get_user_log(GUILD_ID, msg.author.id) is None


async def test_log_activity_ignores_dms(cog):
    msg = make_message(None, "hi")
    msg.channel = MagicMock(spec=discord.DMChannel)
    await cog.log_activity(msg)  # must not touch msg.guild (None)


#################
### bat_react ###
#################


@pytest.fixture
def bats_guild(guild):
    guild.id = SERVERS.BATS
    return guild


@pytest.mark.parametrize(
    "content",
    ["bat", "BATS!", "so batty.", "my batses", "hey <@&1375644186543390781>", "ping <@&1210756079487688774> now"],
)
async def test_bat_react_triggers(cog, bot, bats_guild, content):
    bot.get_emoji = MagicMock(return_value="<:bat_peek:1>")
    msg = make_message(bats_guild, content)
    await cog.bat_react(msg)
    msg.add_reaction.assert_awaited_once_with("<:bat_peek:1>")


@pytest.mark.parametrize("content", ["batman", "acrobat", "hello", "<@&999>"])
async def test_bat_react_no_trigger(cog, bats_guild, content):
    msg = make_message(bats_guild, content)
    await cog.bat_react(msg)
    msg.add_reaction.assert_not_awaited()


async def test_bat_react_falls_back_to_unicode_bat(cog, bot, bats_guild):
    bot.get_emoji = MagicMock(return_value=None)
    msg = make_message(bats_guild, "bats")
    await cog.bat_react(msg)
    msg.add_reaction.assert_awaited_once_with("🦇")


async def test_bat_react_other_guilds_ignored(cog, guild):
    msg = make_message(guild, "bats")  # guild.id is GUILD_ID, not BATS/GLASS_TEST
    await cog.bat_react(msg)
    msg.add_reaction.assert_not_awaited()


async def test_bat_react_ignores_bots(cog, bats_guild):
    msg = make_message(bats_guild, "bats")
    msg.author.bot = True
    await cog.bat_react(msg)
    msg.add_reaction.assert_not_awaited()


###########################
### on_raw_reaction_add ###
###########################


@pytest.fixture
def flag_setup(bot, guild):
    """A message in GUILD_ID, a configured logs channel, and a payload factory."""
    bot.db.update_channel_logs(GUILD_ID, LOGS_CHANNEL_ID)
    logs = make_channel(LOGS_CHANNEL_ID)
    guild.text_channels = [logs]
    msg = make_message(guild, "suspicious content", attachments=[make_attachment("pic.png", "image/png", 10)])
    bot.get_channel = MagicMock(return_value=MagicMock(fetch_message=AsyncMock(return_value=msg)))

    def payload(emoji: str = "🔍", member=None):
        p = MagicMock()
        p.channel_id = 3000
        p.message_id = msg.id
        p.guild_id = GUILD_ID
        p.emoji.name = emoji
        p.member = member or make_member(user_id=2, roles=[make_role(MOD_ROLE_ID, "Mod")])
        return p

    return msg, logs, payload


async def test_mod_flag_logs_message(cog, flag_setup):
    msg, logs, payload = flag_setup
    p = payload()
    await cog.on_raw_reaction_add(p)

    msg.remove_reaction.assert_awaited_once_with("🔍", p.member)
    embed = logs.send.call_args.kwargs["embed"]
    assert embed.title == "Flagged Message"
    values = {f.name: f.value for f in embed.fields}
    assert values["Message content:"] == "suspicious content"
    assert values["Attachment:"] == "pic.png"
    assert f"/{GUILD_ID}/3000/777" in values["Message:"]


async def test_flag_by_non_mod_is_ignored(cog, flag_setup):
    msg, logs, payload = flag_setup
    await cog.on_raw_reaction_add(payload(member=make_member(user_id=9)))
    msg.remove_reaction.assert_not_awaited()
    logs.send.assert_not_awaited()


async def test_other_emoji_is_ignored(cog, flag_setup):
    msg, logs, payload = flag_setup
    await cog.on_raw_reaction_add(payload(emoji="👍"))
    logs.send.assert_not_awaited()


async def test_flag_without_logs_channel_is_ignored(cog, flag_setup, guild):
    msg, logs, payload = flag_setup
    guild.text_channels = []  # configured channel no longer exists
    await cog.on_raw_reaction_add(payload())
    msg.remove_reaction.assert_not_awaited()


async def test_flag_without_mod_roles_is_ignored(cog, flag_setup, bot):
    msg, logs, payload = flag_setup
    bot.db.drop_field(GUILD_ID, "mod_roles")
    await cog.on_raw_reaction_add(payload())
    logs.send.assert_not_awaited()


#######################
### Guild listeners ###
#######################


@pytest.fixture
def harbor_logs(bot):
    """Glass Harbor guild with a logs channel, where guild join/leave notices are sent."""
    harbor = MagicMock()
    harbor.id = SERVERS.GLASS_HARBOR
    logs = make_channel(LOGS_CHANNEL_ID)
    harbor.text_channels = [logs]
    bot.db.add_guild(SERVERS.GLASS_HARBOR, {"guild_id": SERVERS.GLASS_HARBOR, "chan_logs": LOGS_CHANNEL_ID})
    bot.get_guild = MagicMock(return_value=harbor)
    return logs


def make_new_guild(guild_id: int = 8000, name: str = "New Guild") -> MagicMock:
    g = MagicMock()
    g.id = guild_id
    g.name = name
    g.system_channel = None
    return g


async def test_on_guild_join_adds_default_entry(cog, bot, harbor_logs):
    new = make_new_guild()
    await cog.on_guild_join(new)

    assert 8000 in bot.db.get_all_guilds()
    assert bot.db.get_prefix(8000) == ";"
    assert bot.db.get_guild_name(8000) == "New Guild"
    assert "added to database" in harbor_logs.send.call_args.kwargs["embed"].description


async def test_on_guild_join_existing_guild(cog, harbor_logs):
    await cog.on_guild_join(make_new_guild(GUILD_ID, "Test Guild"))
    assert "already in database" in harbor_logs.send.call_args.kwargs["embed"].description


async def test_on_guild_remove(cog, bot, harbor_logs):
    await cog.on_guild_remove(make_new_guild(GUILD_ID, "Test Guild"))
    assert GUILD_ID not in bot.db.get_all_guilds()
    assert "removed from database" in harbor_logs.send.call_args.kwargs["embed"].description


async def test_on_guild_remove_unknown_guild(cog, harbor_logs):
    await cog.on_guild_remove(make_new_guild(8000))
    assert "not found in database" in harbor_logs.send.call_args.kwargs["embed"].description


async def test_on_guild_update_renames(cog, bot, guild):
    new = MagicMock()
    new.name = "Renamed Guild"
    await cog.on_guild_update(guild, new)
    assert bot.db.get_guild_name(GUILD_ID) == "Renamed Guild"


########################
### Member listeners ###
########################


@pytest.fixture
def harbor(bot):
    """Glass Harbor guild (the only guild member join/leave messages are sent in), seeded in the DB."""
    g = MagicMock()
    g.id = SERVERS.GLASS_HARBOR
    g.name = "Glass Harbor"
    g.text_channels = [make_channel(LOGS_CHANNEL_ID), make_channel(WELCOME_CHANNEL_ID)]
    bot.db.add_guild(
        SERVERS.GLASS_HARBOR,
        {"guild_id": SERVERS.GLASS_HARBOR, "chan_logs": LOGS_CHANNEL_ID, "chan_welcome": WELCOME_CHANNEL_ID},
    )
    return g


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (64, 64), (255, 0, 0, 255)).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def fake_avatar(monkeypatch):
    get = MagicMock(return_value=MagicMock(content=_png_bytes()))
    monkeypatch.setattr(httpx, "get", get)
    return get


async def test_on_member_join_sends_welcome_image(cog, harbor, fake_avatar):
    member = make_member(user_id=50, name="newbie")
    member.guild = harbor
    member.display_avatar.url = "https://cdn.example/avatar.png"

    await cog.on_member_join(member)

    fake_avatar.assert_called_once_with("https://cdn.example/avatar.png")
    welcome = harbor.text_channels[1]
    kwargs = welcome.send.call_args.kwargs
    assert kwargs["content"] == "Welcome, <@50>!"
    assert kwargs["embed"].title == "Welcome to Glass Harbor"
    assert kwargs["file"].filename == "image.png"


async def test_on_member_join_other_guild_ignored(cog, guild, fake_avatar):
    member = make_member()
    member.guild = guild
    await cog.on_member_join(member)
    fake_avatar.assert_not_called()


async def test_on_member_join_welcome_channel_disabled(cog, bot, harbor, fake_avatar):
    bot.db.update_channel_welcome(SERVERS.GLASS_HARBOR, 0)
    member = make_member()
    member.guild = harbor
    await cog.on_member_join(member)
    fake_avatar.assert_not_called()


async def test_on_member_join_welcome_channel_unset(cog, bot, harbor, fake_avatar):
    # Regression: an unset welcome channel is None, not 0
    bot.db.drop_field(SERVERS.GLASS_HARBOR, "chan_welcome")
    member = make_member()
    member.guild = harbor
    await cog.on_member_join(member)
    fake_avatar.assert_not_called()


async def test_on_member_remove_says_goodbye_and_drops_log(cog, bot, harbor):
    member = make_member(user_id=60, name="leaver")
    member.guild = harbor
    bot.db.add_or_update_user_log(SERVERS.GLASS_HARBOR, "Glass Harbor", 60, "leaver", datetime(2026, 11, 1))

    await cog.on_member_remove(member)

    embed = harbor.text_channels[0].send.call_args.kwargs["embed"]
    assert embed.title == "Goodbye, leaver!"
    assert bot.db.get_user_log(SERVERS.GLASS_HARBOR, 60) is None


async def test_on_member_remove_no_logs_channel(cog, bot, harbor):
    bot.db.drop_field(SERVERS.GLASS_HARBOR, "chan_logs")
    member = make_member()
    member.guild = harbor
    await cog.on_member_remove(member)
    harbor.text_channels[0].send.assert_not_awaited()


@pytest.mark.xfail(
    reason="BUG: listeners.py:292 returns early for every guild except Glass Harbor, so drop_user_log "
    "(line 305) never runs elsewhere and activity-log entries for departed members are never cleaned up",
    strict=True,
)
async def test_on_member_remove_drops_activity_log_in_any_guild(cog, bot, guild):
    member = make_member(user_id=61)
    member.guild = guild
    bot.db.add_or_update_user_log(GUILD_ID, "Test Guild", 61, "x", datetime(2026, 11, 1))
    await cog.on_member_remove(member)
    assert bot.db.get_user_log(GUILD_ID, 61) is None
