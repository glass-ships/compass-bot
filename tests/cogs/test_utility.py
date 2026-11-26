"""Tests for the Utility cog (debug, emoji/sticker, and misc commands).

Same pattern as test_moderation.py: build the cog with the fake `bot`, then call
`cog._command.callback(cog, ctx, ...)` and assert on what it sent or did.
Filesystem work goes to `tmp_path`; get_resource_path and asyncio.sleep are patched.
"""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from compass.cogs import utility
from compass.cogs.utility import Utility
from compass.config.bot_config import GLASS, SERVERS
from compass.utils.checks import mod_check_ctx
from tests.conftest import GUILD_ID, make_member

###############
### Helpers ###
###############


def make_emoji(name: str, animated: bool = False) -> MagicMock:
    e = MagicMock()
    e.name = name
    e.animated = animated
    e.save = AsyncMock()
    return e


def make_sticker(name: str, emoji: str = "smile", fmt: str = "png") -> MagicMock:
    s = MagicMock()
    s.name = name
    s.emoji = emoji
    s.url = f"https://cdn.example/{name}.{fmt}"
    s.format.name = fmt
    # Like Sticker.save(): writes the image to the given path
    s.save = AsyncMock(side_effect=lambda fp: Path(fp).write_bytes(b"stickerbytes"))
    return s


def embed_text(mock: AsyncMock) -> list[str]:
    """All embed descriptions sent through a mocked `.send`."""
    return [c.kwargs["embed"].description for c in mock.await_args_list if "embed" in c.kwargs]


def sent_text(mock: AsyncMock) -> list[str]:
    """All plain-text messages sent through a mocked `.send`."""
    return [c.args[0] for c in mock.await_args_list if c.args]


################
### Fixtures ###
################


@pytest.fixture
def cog(bot, guild) -> Utility:
    bot.get_guild = MagicMock(return_value=guild)
    bot.guilds = [guild]
    bot.wait_for = AsyncMock()
    c = Utility(bot)
    # discord.py binds command.cog in bot.add_cog(); do it here so commands that call other
    # commands (syncemojis -> self._clear_emojis(ctx, ...)) get `self` passed correctly.
    for cmd in c.__cog_commands__:
        cmd.cog = c
    return c


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(utility.asyncio, "sleep", AsyncMock())


@pytest.fixture
def resource_path(monkeypatch):
    """Patch get_resource_path (no git clone/pull). Set `.return_value` / `.side_effect` per test."""
    fake = MagicMock(return_value=None)
    monkeypatch.setattr(utility, "get_resource_path", fake)
    return fake


@pytest.fixture
def ctx(ctx, guild):
    """conftest ctx, plus the guild-level coroutines the emoji/sticker commands await."""
    guild.delete_emoji = AsyncMock()
    guild.create_custom_emoji = AsyncMock()
    guild.delete_sticker = AsyncMock()
    guild.create_sticker = AsyncMock()
    guild.stickers = []
    guild.get_emoji = MagicMock(return_value=None)
    return ctx


def reply(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    return msg


##############
### Checks ###
##############


def test_all_commands_are_mod_only():
    for cmd in Utility.__cog_commands__:
        assert mod_check_ctx in cmd.checks, cmd.name


######################
### Debug commands ###
######################


async def test_test_command_is_noop(cog, ctx):
    await cog._test.callback(cog, ctx)
    ctx.send.assert_not_awaited()


async def test_clean_activity_log(cog, ctx, guild, bot):
    present = make_member(user_id=30, name="logged")
    absent = make_member(user_id=31, name="unlogged")
    guild.members = [present, absent]
    bot.db.add_or_update_user_log(GUILD_ID, "Test Guild", 30, "logged", __import__("datetime").datetime(2026, 1, 1))

    await cog._clean_activity_log.callback(cog, ctx)

    assert bot.db.get_user_log(GUILD_ID, 30) is None
    texts = sent_text(ctx.send)
    assert "Removing user log for logged" in texts
    assert not any("unlogged" in t for t in texts)
    assert texts[-1] == "Activity log cleaned"


def _slash(name: str) -> MagicMock:
    c = MagicMock(spec=discord.app_commands.Command)
    c.name = name
    return c


def _tree(bot, cmds):
    bot.tree.get_commands = MagicMock(return_value=cmds)
    bot.tree.fetch_commands = AsyncMock(return_value=cmds)


def _group(name: str, subs: list[str]) -> MagicMock:
    g = MagicMock(spec=discord.app_commands.Group)
    g.name = name
    sub_cmds = []
    for s in subs:
        c = _slash(s)
        c.qualified_name = f"{name} {s}"
        sub_cmds.append(c)
    g.walk_commands.return_value = sub_cmds
    return g


def _fetched(name: str, subs: list[str] = ()) -> MagicMock:
    """A command as returned by tree.fetch_commands() (AppCommand, subcommands live in .options)."""
    c = MagicMock(spec=discord.app_commands.AppCommand)
    c.name = name
    c.options = []
    for s in subs:
        o = MagicMock(spec=discord.app_commands.AppCommandGroup)
        o.name = s
        c.options.append(o)
    return c


async def test_get_commands_none(cog, ctx, bot):
    _tree(bot, [])
    await cog._get_commands.callback(cog, ctx)
    (desc,) = embed_text(ctx.channel.send)
    assert desc.count("No commands found") == 4


async def test_get_commands_uses_given_guild_id(cog, ctx, bot):
    _tree(bot, [])
    await cog._get_commands.callback(cog, ctx, "123")
    bot.get_guild.assert_called_once_with(123)


async def test_get_commands_lists_every_command(cog, ctx, bot):
    # Regression: the comprehension iterated i.commands before filtering, crashing on plain Commands
    _tree(bot, [_slash("ping"), _slash("help")])
    await cog._get_commands.callback(cog, ctx)
    (desc,) = embed_text(ctx.channel.send)
    assert "/ping" in desc
    assert "/help" in desc
    assert "\n\n" not in desc.split("__**Guild")[0]  # no doubled newlines between entries


def test_cmds_to_str_local_groups():
    out = utility.cmds_to_str([_slash("ping"), _group("set", ["prefix", "channel"])])
    assert out.splitlines() == ["/ping", "/set prefix", "/set channel"]


def test_cmds_to_str_fetched_commands():
    out = utility.cmds_to_str([_fetched("ping"), _fetched("unset", ["role", "channel"])])
    assert out.splitlines() == ["/ping", "/unset role", "/unset channel"]


def test_cmds_to_str_empty():
    assert utility.cmds_to_str([]) == "No commands found"


async def test_broadcast_ignored_for_non_owner(cog, ctx, bot):
    ctx.author = make_member(user_id=1)
    bot.get_channel = MagicMock()
    await cog.broadcast.callback(cog, ctx, msg="hello")
    bot.get_channel.assert_not_called()


def _broadcast_setup(bot, guild, logs: dict[int, int | None]):
    """Two guilds (the seeded one + 5555) with the given log channel ids; returns {channel_id: fake channel}."""
    other = MagicMock(id=5555)
    other.name = "Other Guild"
    bot.guilds = [guild, other]
    bot.db.update_channel_logs(GUILD_ID, logs[GUILD_ID])
    bot.db.add_guild(5555, {"guild_id": 5555, "chan_logs": logs[5555]})
    channels = {cid: MagicMock(send=AsyncMock()) for cid in logs.values() if cid}
    bot.get_channel = MagicMock(side_effect=channels.get)
    return channels


async def test_broadcast_sends_to_each_guilds_log_channel(cog, ctx, bot, guild):
    # Regression: used ctx.guild's log channel on every iteration -> N copies to the current server
    ctx.author = make_member(user_id=GLASS)
    channels = _broadcast_setup(bot, guild, {GUILD_ID: 111, 5555: 222})

    await cog.broadcast.callback(cog, ctx, msg="hello")

    channels[111].send.assert_awaited_once_with("hello")
    channels[222].send.assert_awaited_once_with("hello")
    assert "2/2" in embed_text(ctx.send)[0]


@pytest.mark.parametrize("unset", [0, None])
async def test_broadcast_skips_guild_without_log_channel(cog, ctx, bot, guild, unset):
    # Regression: a guild without a log channel used to `return`, ending the broadcast for all later guilds
    ctx.author = make_member(user_id=GLASS)
    channels = _broadcast_setup(bot, guild, {GUILD_ID: unset, 5555: 222})

    await cog.broadcast.callback(cog, ctx, msg="hello")

    channels[222].send.assert_awaited_once_with("hello")
    summary = embed_text(ctx.send)[0]
    assert "1/2" in summary
    assert "Test Guild" in summary


async def test_broadcast_skips_deleted_log_channel(cog, ctx, bot, guild):
    ctx.author = make_member(user_id=GLASS)
    channels = _broadcast_setup(bot, guild, {GUILD_ID: 111, 5555: 222})
    del channels[111]  # bot.get_channel(111) -> None

    await cog.broadcast.callback(cog, ctx, msg="hello")

    channels[222].send.assert_awaited_once_with("hello")
    assert "1/2" in embed_text(ctx.send)[0]


async def test_broadcast_continues_after_send_failure(cog, ctx, bot, guild):
    ctx.author = make_member(user_id=GLASS)
    channels = _broadcast_setup(bot, guild, {GUILD_ID: 111, 5555: 222})
    channels[111].send.side_effect = discord.Forbidden(MagicMock(status=403), "Missing Permissions")

    await cog.broadcast.callback(cog, ctx, msg="hello")

    channels[222].send.assert_awaited_once_with("hello")
    summary = embed_text(ctx.send)[0]
    assert "1/2" in summary
    assert "Test Guild" in summary


async def test_clear_commands(cog, ctx, bot):
    bot.tree.clear_commands = MagicMock()
    bot.tree.sync = AsyncMock(return_value=[])
    await cog._clear_commands.callback(cog, ctx)
    bot.tree.clear_commands.assert_called_once()
    assert "0 commands cleared from Test Guild" in embed_text(ctx.send)[0]


######################
### Emoji commands ###
######################


async def test_get_emojis(cog, ctx, guild):
    guild.emojis = [make_emoji("smile"), make_emoji("dance", animated=True)]
    await cog._get_emojis.callback(cog, ctx)
    static_msg, anim_msg = sent_text(ctx.send)
    assert "smile" in static_msg and "dance" not in static_msg
    assert "dance" in anim_msg


async def test_download_emojis_to_resource_dir(cog, ctx, guild, resource_path, tmp_path):
    resource_path.return_value = str(tmp_path)
    smile, dance = make_emoji("smile"), make_emoji("dance", animated=True)
    guild.emojis = [smile, dance]

    await cog._download_emojis.callback(cog, ctx)

    assert (tmp_path / "static").is_dir()
    assert (tmp_path / "animated").is_dir()
    smile.save.assert_awaited_once_with(fp=os.path.join(str(tmp_path), "static/smile.png"))
    dance.save.assert_awaited_once_with(fp=os.path.join(str(tmp_path), "animated/dance.gif"))
    assert "2 emoji's downloaded" in sent_text(ctx.send)


@pytest.mark.usefixtures("resource_path")  # returns None -> fallback dir
async def test_download_emojis_falls_back_to_downloads(cog, ctx, guild, downloads_dir):
    guild.emojis = []
    await cog._download_emojis.callback(cog, ctx)
    assert (downloads_dir / "Test Guild" / "emojis" / "static").is_dir()
    assert (downloads_dir / "Test Guild" / "emojis" / "animated").is_dir()


@pytest.fixture
def emoji_backup(tmp_path, resource_path):
    static, anim = tmp_path / "static", tmp_path / "animated"
    static.mkdir()
    anim.mkdir()
    resource_path.side_effect = lambda _guild_name, *res: str(tmp_path / res[-1])
    return static, anim


@pytest.mark.usefixtures("resource_path")  # returns None -> no backup
async def test_sync_emojis_no_backup(cog, ctx):
    await cog._sync_emojis.callback(cog, ctx)
    assert "**Error**: No emoji backup found." in sent_text(ctx.send)


async def test_sync_emojis_already_synced(cog, ctx, guild, emoji_backup):
    static, anim = emoji_backup
    (static / "smile.webp").write_bytes(b"x")  # any extension, matched by stem
    (anim / "dance.gif").write_bytes(b"x")
    guild.emojis = [make_emoji("smile"), make_emoji("dance", animated=True)]

    await cog._sync_emojis.callback(cog, ctx)

    assert "Emojis already synced!" in embed_text(ctx.send)
    guild.create_custom_emoji.assert_not_awaited()


async def test_sync_emojis_adds_and_removes(cog, ctx, guild, bot, emoji_backup):
    static, anim = emoji_backup
    (static / "new.png").write_bytes(b"png")
    (static / "kept.png").write_bytes(b"png")
    (anim / "party.gif").write_bytes(b"gif")
    kept, stale = make_emoji("kept"), make_emoji("stale")
    guild.emojis = [kept, stale]
    bot.wait_for.return_value = reply("yes")

    await cog._sync_emojis.callback(cog, ctx)

    guild.delete_emoji.assert_awaited_once_with(stale)
    added = {c.kwargs["name"] for c in guild.create_custom_emoji.await_args_list}
    assert added == {"new", "party"}
    assert "Adding 2 emojis and removing 1 emojis" in embed_text(ctx.send)
    assert "Emojis Synced!" in embed_text(ctx.send)


async def test_clear_emojis_nothing_to_remove(cog, ctx, guild, bot):
    guild.emojis = []
    await cog._clear_emojis.callback(cog, ctx)
    assert "No emojis to remove." in embed_text(ctx.channel.send)
    bot.wait_for.assert_not_awaited()


async def test_clear_emojis_confirmed(cog, ctx, guild, bot):
    a, b = make_emoji("a"), make_emoji("b")
    guild.emojis = [a, b]
    bot.wait_for.return_value = reply("Y")

    await cog._clear_emojis.callback(cog, ctx)

    assert [c.args[0] for c in guild.delete_emoji.await_args_list] == [a, b]
    assert "2 emojis removed" in embed_text(ctx.send)


async def test_clear_emojis_only_given_list(cog, ctx, guild, bot):
    a, b = make_emoji("a"), make_emoji("b")
    guild.emojis = [a, b]
    bot.wait_for.return_value = reply("y")
    await cog._clear_emojis.callback(cog, ctx, [b])
    guild.delete_emoji.assert_awaited_once_with(b)


async def test_clear_emojis_cancelled(cog, ctx, guild, bot):
    guild.emojis = [make_emoji("a")]
    bot.wait_for.return_value = reply("no")
    await cog._clear_emojis.callback(cog, ctx)
    guild.delete_emoji.assert_not_awaited()
    assert "Command cancelled." in embed_text(ctx.send)


async def test_clear_emojis_timeout(cog, ctx, guild, bot):
    guild.emojis = [make_emoji("a")]
    bot.wait_for.side_effect = TimeoutError
    await cog._clear_emojis.callback(cog, ctx)
    guild.delete_emoji.assert_not_awaited()
    assert "Command timed out after 30 sec." in embed_text(ctx.send)


async def test_clear_emojis_check_only_accepts_author_in_channel(cog, ctx, guild, bot):
    guild.emojis = [make_emoji("a")]
    bot.wait_for.return_value = reply("n")
    await cog._clear_emojis.callback(cog, ctx)
    check = bot.wait_for.call_args.kwargs["check"]
    assert check(MagicMock(author=ctx.author, channel=ctx.channel)) is True
    assert check(MagicMock(author=make_member(user_id=99), channel=ctx.channel)) is False
    assert check(MagicMock(author=ctx.author, channel=MagicMock())) is False


async def test_add_emojis_uses_stem_and_reports_errors(cog, ctx, guild, tmp_path):
    good, bad = tmp_path / "illegible.webp", tmp_path / "broken.png"
    good.write_bytes(b"img")
    bad.write_bytes(b"img")
    guild.create_custom_emoji.side_effect = [None, RuntimeError("400 Bad Request")]

    await cog._add_emojis(ctx, [str(good), str(bad)])

    assert guild.create_custom_emoji.await_args_list[0].kwargs == {"name": "illegible", "image": b"img"}
    assert any("400 Bad Request" in t for t in sent_text(ctx.send))
    assert "2 emojis added" in embed_text(ctx.channel.send)


########################
### Sticker commands ###
########################


async def test_get_stickers(cog, ctx, guild):
    guild.stickers = [make_sticker("wave")]
    await cog._get_stickers.callback(cog, ctx)
    assert "wave" in sent_text(ctx.send)[0]


async def test_download_stickers(cog, ctx, guild, resource_path, tmp_path):
    resource_path.return_value = str(tmp_path)
    s = make_sticker("wave", emoji="smile")
    guild.stickers = [s]

    await cog._download_stickers.callback(cog, ctx)

    s.save.assert_awaited_once_with(f"{tmp_path}/wave_smile.png")
    assert (tmp_path / "wave_smile.png").read_bytes() == b"stickerbytes"
    assert "1 stickers downloaded" in embed_text(ctx.send)


async def test_download_stickers_skips_lottie(cog, ctx, guild, resource_path, tmp_path):
    resource_path.return_value = str(tmp_path)
    lottie = make_sticker("dance", fmt="lottie")
    lottie.save.side_effect = TypeError('Cannot read stickers of format "lottie".')
    guild.stickers = [lottie, make_sticker("wave")]

    await cog._download_stickers.callback(cog, ctx)

    assert [p.name for p in tmp_path.iterdir()] == ["wave_smile.png"]
    assert "Skipped `dance`: lottie stickers can't be downloaded." in sent_text(ctx.send)
    assert "1 stickers downloaded" in embed_text(ctx.send)


@pytest.mark.usefixtures("resource_path")
async def test_download_stickers_falls_back_to_downloads(cog, ctx, guild, downloads_dir):
    guild.stickers = [make_sticker("wave")]
    await cog._download_stickers.callback(cog, ctx)
    assert (downloads_dir / "Test Guild" / "stickers" / "wave_smile.png").exists()


async def test_download_stickers_with_custom_emoji(cog, ctx, guild, resource_path, tmp_path):
    resource_path.return_value = str(tmp_path)
    guild.stickers = [make_sticker("wave", emoji="1234")]
    guild.get_emoji = MagicMock()

    await cog._download_stickers.callback(cog, ctx)

    assert [p.name for p in tmp_path.iterdir()] == ["wave_1234.png"]
    guild.get_emoji.assert_not_called()


async def test_sticker_backup_round_trip_keeps_custom_emoji_id(cog, ctx, guild, resource_path, tmp_path):
    resource_path.return_value = str(tmp_path)
    guild.stickers = [make_sticker("wave", emoji="1234")]
    await cog._download_stickers.callback(cog, ctx)

    guild.stickers = []  # e.g. syncing into a fresh guild that doesn't have the custom emoji
    await cog._sync_stickers.callback(cog, ctx)

    guild.create_sticker.assert_awaited_once()
    assert guild.create_sticker.call_args.kwargs["name"] == "wave"
    assert guild.create_sticker.call_args.kwargs["emoji"] == "1234"


@pytest.mark.usefixtures("resource_path")  # returns None -> no backup
async def test_sync_stickers_no_backup(cog, ctx):
    await cog._sync_stickers.callback(cog, ctx)
    assert "**Error**: No sticker backup found." in sent_text(ctx.send)


async def test_sync_stickers_adds_missing(cog, ctx, guild, resource_path, tmp_path):
    resource_path.return_value = str(tmp_path)
    (tmp_path / "wave_smile.png").write_bytes(b"x")
    guild.stickers = []

    await cog._sync_stickers.callback(cog, ctx)

    guild.create_sticker.assert_awaited_once()
    assert guild.create_sticker.call_args.kwargs["name"] == "wave"
    assert guild.create_sticker.call_args.kwargs["emoji"] == "smile"
    assert "Stickers Synced!" in embed_text(ctx.send)


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("wave_smile.png", ("wave", "smile")),
        ("who me.png", ("who me", None)),  # no emoji
        ("bonnie quirky_stuck_out_tongue_winking_eye.png", ("bonnie quirky", "stuck_out_tongue_winking_eye")),
        ("jerkin_🌶️.gif", ("jerkin", "🌶️")),
        ("pog_1234.png", ("pog", "1234")),  # custom emoji ID
    ],
)
def test_parse_sticker_filename(filename, expected):
    assert utility.parse_sticker_filename(filename) == expected


def test_sticker_filename_round_trips():
    filename = utility.sticker_filename("bonnie quirky", "stuck_out_tongue_winking_eye", "png")
    assert utility.parse_sticker_filename(filename) == ("bonnie quirky", "stuck_out_tongue_winking_eye")


@pytest.mark.parametrize(
    "filename, sticker",
    [
        pytest.param("wave_smile.png", make_sticker("wave", emoji="smile"), id="as written by downloadstickers"),
        pytest.param("wave_smile.png", make_sticker("wave", emoji="grin"), id="emoji changed since backup"),
        pytest.param("who me.png", make_sticker("who me"), id="no emoji in filename"),
        pytest.param(
            "bonnie quirky_stuck_out_tongue_winking_eye.png",
            make_sticker("bonnie quirky", emoji="stuck_out_tongue_winking_eye"),
            id="underscores in emoji",
        ),
    ],
)
async def test_sync_stickers_keeps_backed_up_sticker(cog, ctx, guild, bot, resource_path, tmp_path, filename, sticker):
    # Regression: compared against '{name}.{format}', so every backed-up sticker was flagged for removal
    resource_path.return_value = str(tmp_path)
    (tmp_path / filename).write_bytes(b"x")
    guild.stickers = [sticker]
    bot.wait_for.return_value = reply("y")

    await cog._sync_stickers.callback(cog, ctx)

    guild.delete_sticker.assert_not_awaited()
    guild.create_sticker.assert_not_awaited()


async def test_sync_stickers_removes_sticker_not_in_backup(cog, ctx, guild, bot, resource_path, tmp_path):
    resource_path.return_value = str(tmp_path)
    (tmp_path / "wave_smile.png").write_bytes(b"x")
    keep, extra = make_sticker("wave"), make_sticker("extra")
    guild.stickers = [keep, extra]
    bot.wait_for.return_value = reply("y")

    await cog._sync_stickers.callback(cog, ctx)

    guild.delete_sticker.assert_awaited_once_with(extra)
    guild.create_sticker.assert_not_awaited()


async def test_clear_stickers_nothing_to_remove(cog, ctx, bot):
    await cog._clear_stickers.callback(cog, ctx)
    assert "No stickers to remove." in embed_text(ctx.channel.send)
    bot.wait_for.assert_not_awaited()


async def test_clear_stickers_confirmed(cog, ctx, guild, bot):
    s = make_sticker("wave")
    guild.stickers = [s]
    bot.wait_for.return_value = reply("yes")
    await cog._clear_stickers.callback(cog, ctx)
    guild.delete_sticker.assert_awaited_once_with(s)
    assert "1 stickers removed" in embed_text(ctx.send)


async def test_clear_stickers_cancelled(cog, ctx, guild, bot):
    guild.stickers = [make_sticker("wave")]
    bot.wait_for.return_value = reply("nope")
    await cog._clear_stickers.callback(cog, ctx)
    guild.delete_sticker.assert_not_awaited()
    assert "Command cancelled." in embed_text(ctx.send)


async def test_clear_stickers_timeout(cog, ctx, guild, bot):
    guild.stickers = [make_sticker("wave")]
    bot.wait_for.side_effect = TimeoutError
    await cog._clear_stickers.callback(cog, ctx)
    guild.delete_sticker.assert_not_awaited()
    assert "Command timed out after 30 sec." in embed_text(ctx.send)


async def test_add_stickers_name_and_emoji_parsing(cog, ctx, guild, tmp_path):
    no_emoji = tmp_path / "plain.png"
    custom = tmp_path / "pog_1234.png"
    for p in (no_emoji, custom):
        p.write_bytes(b"x")
    guild.get_emoji = MagicMock()
    guild.create_sticker.side_effect = [None, RuntimeError("boom")]

    await cog._add_stickers(ctx, [no_emoji.as_posix(), custom.as_posix()])

    first, second = guild.create_sticker.await_args_list
    assert first.kwargs["name"] == "plain" and first.kwargs["emoji"] == "❓"
    assert second.kwargs["name"] == "pog" and second.kwargs["emoji"] == "1234"
    guild.get_emoji.assert_not_called()
    assert any("boom" in t for t in sent_text(ctx.send))
    assert "2 stickers added" in embed_text(ctx.send)


#####################
### Misc commands ###
#####################


async def test_resources(cog, ctx, resource_path):
    resource_path.return_value = "/some/path"
    await cog._resources.callback(cog, ctx)
    assert "`/some/path`" in sent_text(ctx.send)[0]


async def test_clear_downloads(cog, ctx, downloads_dir):
    (downloads_dir / "x").mkdir(parents=True)
    await cog._clear_downloads.callback(cog, ctx)
    assert not downloads_dir.exists()
    ctx.message.delete.assert_awaited_once()
    ctx.send.assert_awaited_once_with("Downloads cleared!", delete_after=2.0)


async def test_clear_downloads_when_empty(cog, ctx, downloads_dir):
    # Regression: raised FileNotFoundError when there was nothing to clear
    assert not downloads_dir.exists()
    await cog._clear_downloads.callback(cog, ctx)
    ctx.message.delete.assert_awaited_once()
    ctx.send.assert_awaited_once_with("Nothing to clear.", delete_after=2.0)


async def test_download_rejected_outside_glass_servers(cog, ctx):
    # Regression: replied via ctx.response.send_message, which a prefix command's Context doesn't have
    ctx = MagicMock(spec=["guild", "channel", "send"], guild=MagicMock(id=1), send=AsyncMock())
    await cog._download.callback(cog, ctx)
    ctx.send.assert_awaited_once()


async def test_download_saves_attachments(cog, ctx, guild, downloads_dir):
    guild.id = SERVERS.GLASS_TEST
    ctx.channel.name = "general"
    ok = MagicMock(filename="a.png", save=AsyncMock())
    failing = MagicMock(filename="b.png", save=AsyncMock(side_effect=RuntimeError("disk full")))

    async def history():
        yield MagicMock(attachments=[ok, failing], id=1)
        yield MagicMock(attachments=[], id=2)

    ctx.channel.history = history

    await cog._download.callback(cog, ctx)

    assert (downloads_dir / "Test Guild" / "general").is_dir()
    ok.save.assert_awaited_once_with(fp=downloads_dir / "Test Guild" / "general" / "a.png")
    texts = sent_text(ctx.send)
    assert any("disk full" in t for t in texts)
    assert texts[-1] == "Success: Downloaded 2 items."
