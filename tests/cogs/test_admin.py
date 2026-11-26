"""Tests for the Admin cog (sync/reload debug commands and the /set, /unset, /allowvideos settings commands).

See tests/cogs/test_moderation.py for the general pattern. DB writes are verified by reading back
from the `bot` fixture's in-memory (mongomock) ServerDB.
"""

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord import app_commands
from discord.ext import commands

from compass.cogs.admin import Admin
from compass.config.bot_config import CHANNEL_OPTIONS, MODULES, ROLE_OPTIONS
from tests.conftest import GUILD_ID, MOD_ROLE_ID, make_role


@pytest.fixture
def cog(bot) -> Admin:
    bot.tree.sync = AsyncMock(return_value=[object(), object()])  # "synced 2 commands"
    bot.tree.clear_commands = MagicMock()
    bot.tree.copy_global_to = MagicMock()
    bot.reload_extension = AsyncMock()
    return Admin(bot)


@pytest.fixture
def status_msg(ctx) -> MagicMock:
    """The embed message _sync sends first and then keeps editing."""
    msg = MagicMock(edit=AsyncMock())
    ctx.send.return_value = msg
    return msg


def _last_edit(msg: MagicMock) -> str:
    return msg.edit.call_args.kwargs["embed"].description


def _channel(channel_id: int = 555) -> MagicMock:
    return MagicMock(id=channel_id)


def _sent(itx) -> str:
    return itx.response.send_message.call_args.args[0]


def _choices(command, param: str = "option") -> list[str]:
    """The fixed choice values Discord is given for a slash command parameter."""
    (p,) = [p for p in command.parameters if p.name == param]
    return [c.value for c in p.choices]


def _assert_unknown_option_reply(itx, options: list[str]) -> None:
    itx.response.send_message.assert_awaited_once()
    assert "Unknown option" in _sent(itx)
    assert all(o in _sent(itx) for o in options)
    assert itx.response.send_message.call_args.kwargs["ephemeral"] is True


##############
### Checks ###
##############

ADMIN_SLASH_COMMANDS = [
    "_prefix",
    "_track_activity",
    "_mod_roles",
    "_member_role",
    "_required_roles",
    "_role",
    "_channel_set",
    "_allowvideos",
]


@pytest.mark.parametrize("command", ADMIN_SLASH_COMMANDS)
def test_admin_slash_commands_require_administrator(command, itx):
    checks = getattr(Admin, command).checks
    assert len(checks) == 1
    (check,) = checks

    itx.permissions = discord.Permissions(administrator=True)
    assert check(itx) is True

    itx.permissions = discord.Permissions.none()
    with pytest.raises(app_commands.MissingPermissions):
        check(itx)


@pytest.mark.parametrize(
    "command",
    [
        pytest.param("_reload", id="reload"),
        pytest.param("_channel_unset", id="unset channel"),
    ],
)
def test_slash_commands_have_permission_checks(command):
    # Regression: these used @commands.has_permissions, which discord.py ignores on slash commands
    assert getattr(Admin, command).checks


def test_sync_requires_administrator(ctx):
    (check,) = Admin._sync.checks
    ctx.permissions = discord.Permissions(administrator=True)
    assert check(ctx) is True
    ctx.permissions = discord.Permissions.none()
    with pytest.raises(commands.MissingPermissions):
        check(ctx)


def test_on_ready_is_a_listener():
    assert ("on_ready", "on_ready") in Admin.__cog_listeners__


async def test_on_ready_logs(cog, caplog):
    caplog.set_level("INFO")
    await cog.on_ready()
    assert "Cog Online: Admin" in caplog.text


############
### sync ###
############


async def test_sync_all_guilds(cog, ctx, status_msg, bot):
    g1, g2 = MagicMock(), MagicMock()
    g1.name, g2.name = "One", "Two"
    bot.guilds = [g1, g2]

    await cog._sync.callback(cog, ctx, sync_args="")

    assert [c.kwargs["guild"] for c in bot.tree.sync.await_args_list] == [g1, g2]
    bot.tree.copy_global_to.assert_not_called()
    bot.tree.clear_commands.assert_not_called()
    desc = _last_edit(status_msg)
    assert "Synced 2 commands to guild: One (1/2)." in desc
    assert "Synced 2 commands to guild: Two (2/2)." in desc
    assert desc.endswith("Sync complete!")


async def test_sync_all_guilds_dev_copies_globals(cog, ctx, status_msg, bot):
    g = MagicMock()
    g.name = "One"
    bot.guilds = [g]

    await cog._sync.callback(cog, ctx, sync_args="--dev")

    bot.tree.copy_global_to.assert_called_once_with(guild=g)
    assert "Copying global commands to guild: One (1/1)" in _last_edit(status_msg)


async def test_sync_current_guild_only(cog, ctx, status_msg, bot):
    bot.guilds = [MagicMock(), MagicMock()]

    await cog._sync.callback(cog, ctx, sync_args="--guild")

    bot.tree.sync.assert_awaited_once_with(guild=ctx.guild)
    desc = _last_edit(status_msg)
    assert desc.endswith("Synced 2 commands to guild.")
    assert "Sync complete!" not in desc  # the guild branch returns early


async def test_sync_current_guild_dev_and_clean(cog, ctx, status_msg, bot):
    await cog._sync.callback(cog, ctx, sync_args="--guild --dev --clean")

    bot.tree.clear_commands.assert_called_once_with(guild=ctx.guild)
    bot.tree.copy_global_to.assert_called_once_with(guild=ctx.guild)
    bot.tree.sync.assert_awaited_once_with(guild=ctx.guild)
    desc = _last_edit(status_msg)
    assert "Clearing command tree from Test Guild" in desc
    assert "Copying global commands to guild: Test Guild" in desc


async def test_sync_clean_all_guilds(cog, ctx, status_msg, bot):
    bot.guilds = []
    await cog._sync.callback(cog, ctx, sync_args="--clean")

    bot.tree.clear_commands.assert_called_once_with(guild=None)
    assert "Clearing command tree from all guilds" in _last_edit(status_msg)


#########################################
### _sync_umbra (helper, not a command) ###
#########################################


@pytest.fixture
def umbra_ctx(ctx) -> MagicMock:
    ctx.bot.tree.sync = AsyncMock(return_value=[object()] * 3)
    ctx.bot.tree.copy_global_to = MagicMock()
    ctx.bot.tree.clear_commands = MagicMock()
    return ctx


@pytest.mark.parametrize(
    "spec, expected_msg",
    [
        (None, "Synced 3 commands globally"),
        ("~", "Synced 3 commands to the current guild."),
        ("*", "Synced 3 commands to the current guild."),
        ("^", "Synced 0 commands to the current guild."),
    ],
)
async def test_sync_umbra_specs(cog, umbra_ctx, spec, expected_msg):
    await cog._sync_umbra(umbra_ctx, [], spec)

    tree = umbra_ctx.bot.tree
    if spec is None:
        tree.sync.assert_awaited_once_with()
    else:
        tree.sync.assert_awaited_once_with(guild=umbra_ctx.guild)
    assert tree.copy_global_to.called is (spec == "*")
    assert tree.clear_commands.called is (spec == "^")
    umbra_ctx.send.assert_awaited_once_with(expected_msg)


async def test_sync_umbra_specific_guilds_counts_failures(cog, umbra_ctx):
    ok, bad = MagicMock(), MagicMock()

    async def sync(guild):
        if guild is bad:
            raise discord.HTTPException(MagicMock(status=500), "boom")
        return []

    umbra_ctx.bot.tree.sync = AsyncMock(side_effect=sync)
    await cog._sync_umbra(umbra_ctx, [ok, bad, ok])

    umbra_ctx.send.assert_awaited_once_with("Synced the tree to 2/3.")


##############
### reload ###
##############


async def test_reload_success(cog, itx, bot):
    await cog._reload.callback(cog, itx, "music")

    bot.reload_extension.assert_awaited_once_with("cogs.music")
    assert "`music` reloaded" in _sent(itx)
    assert itx.response.send_message.call_args.kwargs["ephemeral"] is True


async def test_reload_error_is_reported(cog, itx, bot):
    bot.reload_extension.side_effect = commands.ExtensionNotLoaded("cogs.nope")

    await cog._reload.callback(cog, itx, "nope")

    assert "Error" in _sent(itx)
    assert "cogs.nope" in _sent(itx)


async def test_reload_autocomplete(cog, itx):
    assert MODULES, "expected at least one cog module"
    target = MODULES[0]

    choices = await Admin._reload_autocomplete(cog, itx, target[:2].upper())

    assert target in [c.value for c in choices]
    assert all(target[:2].lower() in c.value.lower() for c in choices)
    assert await Admin._reload_autocomplete(cog, itx, "zzz-no-such-module") == []


####################
### set commands ###
####################


async def test_set_prefix(cog, itx, bot):
    await cog._prefix.callback(cog, itx, "!")
    assert bot.db.get_prefix(GUILD_ID) == "!"
    assert _sent(itx) == "Prefix set to `!`"


@pytest.mark.parametrize("track", [True, False])
async def test_set_track_activity(cog, itx, bot, track):
    await cog._track_activity.callback(cog, itx, track)
    assert bot.db.get_field(GUILD_ID, "track_activity") is track
    assert _sent(itx) == f"Activity tracking set to `{track}`"


@pytest.mark.parametrize(
    "command, getter",
    [("_mod_roles", "get_mod_roles"), ("_required_roles", "get_required_roles")],
)
@pytest.mark.parametrize(
    "arg, expected",
    [
        ("123", [123]),
        ("<@&123>", [123]),
        ("<@&123> 456 <@&789>", [123, 456, 789]),
    ],
)
async def test_set_role_lists(cog, itx, bot, command, getter, arg, expected):
    await getattr(cog, command).callback(cog, itx, arg)
    assert getattr(bot.db, getter)(GUILD_ID) == expected
    assert arg in _sent(itx)


async def test_set_mod_roles_tolerates_extra_whitespace(cog, itx, bot):
    # Regression: split(" ") turned a double space into int("")
    await cog._mod_roles.callback(cog, itx, "<@&123>  456")
    assert bot.db.get_mod_roles(GUILD_ID) == [123, 456]


@pytest.mark.parametrize("command", ["_mod_roles", "_required_roles"])
@pytest.mark.parametrize(
    "bad",
    [
        pytest.param("abc", id="non-numeric"),
        pytest.param("<@123>", id="user mention"),
        pytest.param("<#123>", id="channel mention"),
    ],
)
async def test_set_roles_invalid_input_replies_with_error(cog, itx, bot, command, bad):
    # Regression: invalid input raised unhandled, so the user got "The application did not respond"
    await getattr(cog, command).callback(cog, itx, f"456 {bad}")
    itx.response.send_message.assert_awaited_once()
    assert bad in itx.response.send_message.call_args.args[0]
    assert itx.response.send_message.call_args.kwargs["ephemeral"] is True
    assert bot.db.get_mod_roles(GUILD_ID) == [MOD_ROLE_ID]  # nothing saved
    assert bot.db.get_required_roles(GUILD_ID) == []


async def test_set_member_role(cog, itx, bot):
    role = make_role(77, "Member")
    await cog._member_role.callback(cog, itx, role)
    assert bot.db.get_mem_role(GUILD_ID) == 77
    itx.response.send_message.assert_awaited_once()


######################
### unset role ###
######################


@pytest.mark.parametrize(
    "option, getter",
    [("mod", "get_mod_roles"), ("member", "get_mem_role"), ("required", "get_required_roles")],
)
async def test_unset_role(cog, itx, bot, option, getter):
    assert await cog._role.callback(cog, itx, option) is True
    assert getattr(bot.db, getter)(GUILD_ID) is None
    assert _sent(itx) == f"{option.title()} role unset."


async def test_unset_role_unknown_option(cog, itx, bot):
    # Unreachable from Discord (fixed choices), but the fallback must still reply
    assert await cog._role.callback(cog, itx, "bogus") is False
    _assert_unknown_option_reply(itx, ROLE_OPTIONS)
    assert bot.db.get_mod_roles(GUILD_ID) == [MOD_ROLE_ID]  # untouched


def test_unset_role_choices():
    assert _choices(Admin._role) == ROLE_OPTIONS


########################
### set/unset channel ###
########################

CHANNEL_GETTERS = {
    "bot": "get_channel_bot",
    "logs": "get_channel_logs",
    "welcome": "get_channel_welcome",
    "music": "get_channel_music",
    "lfg": "get_channel_lfg",
    "videos": "get_channel_vids",
}


def test_channel_getters_cover_all_options():
    assert set(CHANNEL_GETTERS) == set(CHANNEL_OPTIONS)


@pytest.mark.parametrize("option, getter", CHANNEL_GETTERS.items())
async def test_set_channel(cog, itx, bot, option, getter):
    assert await cog._channel_set.callback(cog, itx, option, _channel(555)) is True
    assert getattr(bot.db, getter)(GUILD_ID) == 555
    assert _sent(itx) == f"{option.title()} channel set to <#555>."


async def test_set_channel_unknown_option_responds(cog, itx, bot):
    before = {g: getattr(bot.db, g)(GUILD_ID) for g in CHANNEL_GETTERS.values()}
    assert await cog._channel_set.callback(cog, itx, "bogus", _channel()) is False
    _assert_unknown_option_reply(itx, CHANNEL_OPTIONS)
    assert {g: getattr(bot.db, g)(GUILD_ID) for g in CHANNEL_GETTERS.values()} == before  # nothing saved


@pytest.mark.parametrize("option, getter", CHANNEL_GETTERS.items())
async def test_unset_channel(cog, itx, bot, option, getter):
    bot.db.add_or_update_field(GUILD_ID, f"chan_{'vids' if option == 'videos' else option}", 555)

    assert await cog._channel_unset.callback(cog, itx, option) is True
    assert getattr(bot.db, getter)(GUILD_ID) is None
    assert _sent(itx) == f"{option.title()} channel unset."


async def test_unset_channel_unknown_option(cog, itx):
    assert await cog._channel_unset.callback(cog, itx, "bogus") is False
    _assert_unknown_option_reply(itx, CHANNEL_OPTIONS)


@pytest.mark.parametrize("command", ["_channel_set", "_channel_unset"])
def test_channel_choices(command):
    assert _choices(getattr(Admin, command)) == CHANNEL_OPTIONS


###################
### allowvideos ###
###################


async def test_allowvideos_true_then_false(cog, itx, bot):
    await cog._allowvideos.callback(cog, itx, _channel(9), True)
    assert bot.db.get_videos_whitelist(GUILD_ID) == [9]
    assert _sent(itx) == "Videos allowed in <#9>."

    await cog._allowvideos.callback(cog, itx, _channel(9), False)
    assert bot.db.get_videos_whitelist(GUILD_ID) == []
    assert _sent(itx) == "Videos not allowed in <#9>."
