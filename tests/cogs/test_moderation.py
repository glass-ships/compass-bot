"""Tests for the Moderation cog.

Pattern for testing any cog command:
    cog = Moderation(bot)                                  # sets the module's `global bot`
    await cog._command.callback(cog, itx_or_ctx, *args)    # call the command function directly
    itx.followup.send.assert_awaited_...                   # assert on what it sent / did

`.callback` exists on both `@app_commands.command` and `@commands.command` objects; it bypasses
discord.py's dispatch, so checks (like has_mod_itx) are NOT run - test those separately.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from compass.cogs import moderation
from compass.cogs.moderation import Moderation
from compass.utils.checks import mod_check_itx
from tests.conftest import GUILD_ID, make_member, make_role


@pytest.fixture
def cog(bot) -> Moderation:
    return Moderation(bot)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Make asyncio.sleep instant inside the cog (giverole/removerole durations, mod check delays)."""
    monkeypatch.setattr(moderation.asyncio, "sleep", AsyncMock())


##############
### Checks ###
##############


@pytest.mark.parametrize("command", ["_give_role", "_take_role", "_send", "_send_dm", "_purge", "_check_roles"])
def test_mod_only_commands_have_mod_check(command):
    assert mod_check_itx in getattr(Moderation, command).checks


################
### giverole ###
################


@pytest.fixture
def admin_caller(itx):
    """The invoking user is an admin, so can_manage_role allows any role."""
    itx.user.guild_permissions.administrator = True
    return itx.user


@pytest.mark.usefixtures("admin_caller")
async def test_giverole_adds_role(cog, itx, guild, member):
    role = make_role(42, "VIP")
    guild.roles = [role]

    await cog._give_role.callback(cog, itx, role, member, None)

    itx.response.defer.assert_awaited_once()  # without this, followup.send 404s ("Unknown Webhook")
    member.add_roles.assert_awaited_once_with(role)
    assert '"VIP"' in itx.followup.send.call_args.args[0]


@pytest.mark.usefixtures("admin_caller")
async def test_giverole_with_duration_removes_role_afterwards(cog, itx, guild, member):
    role = make_role(42, "VIP")
    guild.roles = [role]

    await cog._give_role.callback(cog, itx, role, member, 60)

    moderation.asyncio.sleep.assert_awaited_once_with(60)
    member.remove_roles.assert_awaited_once_with(role)
    assert "removed" in itx.channel.send.call_args.args[0]


@pytest.mark.usefixtures("admin_caller")
async def test_giverole_user_already_has_role(cog, itx, guild):
    role = make_role(42, "VIP")
    guild.roles = [role]
    user = make_member(roles=[role])

    await cog._give_role.callback(cog, itx, role, user, None)

    user.add_roles.assert_not_awaited()
    assert "already has it" in itx.followup.send.call_args.args[0]


##################
### removerole ###
##################


@pytest.mark.usefixtures("admin_caller")
async def test_removerole(cog, itx, guild):
    role = make_role(42, "VIP")
    guild.roles = [role]
    user = make_member(roles=[role])

    await cog._take_role.callback(cog, itx, role, user, None)

    user.remove_roles.assert_awaited_once_with(role)
    assert "removed" in itx.followup.send.call_args.args[0]  # answers the deferred interaction


@pytest.mark.usefixtures("admin_caller")
async def test_removerole_with_duration_adds_role_back(cog, itx, guild):
    role = make_role(42, "VIP")
    guild.roles = [role]
    user = make_member(roles=[role])

    await cog._take_role.callback(cog, itx, role, user, 60)

    moderation.asyncio.sleep.assert_awaited_once_with(60)
    user.add_roles.assert_awaited_once_with(role)
    # channel.send, not followup: the interaction token may have expired by then
    assert "added back" in itx.channel.send.call_args.args[0]


#########################
### role hierarchy ###
#########################


@pytest.fixture
def mod_caller(itx) -> MagicMock:
    """A non-admin, non-owner caller whose top role is at position 5."""
    itx.user.guild_permissions.administrator = False
    itx.user.top_role = make_role(1, "Mod", position=5)
    itx.user.guild.owner = MagicMock()
    return itx.user


@pytest.mark.usefixtures("mod_caller")
@pytest.mark.parametrize("command", ["_give_role", "_take_role"])
@pytest.mark.parametrize("position", [pytest.param(5, id="own top role"), pytest.param(6, id="above")])
async def test_role_commands_refuse_role_not_below_caller(cog, itx, guild, command, position):
    # Regression: no hierarchy check, so a mod could give themselves (or strip) roles above their own
    role = make_role(42, "Admin", position=position)
    guild.roles = [role]
    target = make_member(roles=[role] if command == "_take_role" else [])

    await getattr(cog, command).callback(cog, itx, role, target, None)

    target.add_roles.assert_not_awaited()
    target.remove_roles.assert_not_awaited()
    assert itx.followup.send.call_args.kwargs["ephemeral"] is True


@pytest.mark.usefixtures("mod_caller")
@pytest.mark.parametrize("command", ["_give_role", "_take_role"])
async def test_role_commands_allow_role_below_caller(cog, itx, guild, command):
    role = make_role(42, "VIP", position=4)
    guild.roles = [role]
    target = make_member(roles=[role] if command == "_take_role" else [])

    await getattr(cog, command).callback(cog, itx, role, target, None)

    changed = target.remove_roles if command == "_take_role" else target.add_roles
    changed.assert_awaited_once_with(role)


def test_can_manage_role_admin_and_owner_bypass_hierarchy():
    high = make_role(42, "Top", position=99)
    admin = make_member(admin=True)
    admin.top_role = make_role(1, position=1)
    assert moderation.can_manage_role(admin, high)

    owner = make_member()
    owner.top_role = make_role(1, position=1)
    owner.guild.owner = owner
    assert moderation.can_manage_role(owner, high)


@pytest.mark.usefixtures("admin_caller")
async def test_removerole_user_lacks_role(cog, itx, guild, member):
    role = make_role(42, "VIP")
    guild.roles = [role]

    await cog._take_role.callback(cog, itx, role, member, None)

    member.remove_roles.assert_not_awaited()
    assert "doesn't have it" in itx.followup.send.call_args.args[0]


#############
### purge ###
#############


@pytest.fixture
def purge_channel(itx) -> AsyncMock:
    itx.channel.purge = AsyncMock(return_value=[object()] * 3)  # 3 messages actually deleted
    return itx.channel.purge


async def test_purge_deletes_and_reports_actual_count(cog, itx, purge_channel):
    await cog._purge.callback(cog, itx, 10)

    # ephemeral: a public "thinking..." message would be in the channel and could be purged
    itx.response.defer.assert_awaited_once_with(ephemeral=True)
    purge_channel.assert_awaited_once_with(limit=10, before=None, after=None, reason=None)
    itx.followup.send.assert_awaited_once_with("3 messages purged.", ephemeral=True)


# dateparser triggers a CPython strptime DeprecationWarning internally (not from our code)
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
async def test_purge_passes_parsed_times(cog, itx, purge_channel):
    await cog._purge.callback(cog, itx, 10, before="2026-01-02 12:00", after="2026-01-01 12:00")

    kwargs = purge_channel.call_args.kwargs
    assert isinstance(kwargs["before"], datetime)
    assert isinstance(kwargs["after"], datetime)
    assert kwargs["after"] < kwargs["before"]


@pytest.mark.parametrize("field", ["before", "after"])
async def test_purge_unparseable_time_deletes_nothing(cog, itx, purge_channel, field):
    # Regression: unparseable text became None, i.e. no filter, so the latest messages were purged instead
    await cog._purge.callback(cog, itx, 10, **{field: "not a time at all"})

    purge_channel.assert_not_awaited()
    assert "nothing was deleted" in itx.followup.send.call_args.args[0]


def test_purge_number_is_required_and_bounded():
    # Regression: number defaulted to None, and purge(limit=None) deletes the entire channel
    (param,) = [p for p in Moderation._purge.parameters if p.name == "number"]
    assert param.required
    assert (param.min_value, param.max_value) == (1, 1000)


#####################
### send / dm ###
#####################


async def test_send(cog, itx):
    channel = MagicMock(id=555, send=AsyncMock())
    await cog._send.callback(cog, itx, channel, "hello")
    channel.send.assert_awaited_once_with(content="hello")
    assert "<#555>" in itx.followup.send.call_args.args[0]


async def test_dm(cog, itx, member):
    await cog._send_dm.callback(cog, itx, member, "hi there")
    member.send.assert_awaited_once_with(content="hi there")


####################
### getmodroles ###
####################


async def test_getmodroles_lists_roles_from_db(cog, itx):
    await cog._get_mod_roles.callback(cog, itx)
    embed = itx.response.send_message.call_args.kwargs["embed"]
    assert "<@&2000>" in embed.description


##################
### checkroles ###
##################


async def test_checkroles_none_configured(cog, itx):
    await cog._check_roles.callback(cog, itx)
    itx.followup.send.assert_awaited_once_with("No required roles set.")


async def test_checkroles_lists_members_missing_roles(cog, itx, guild, bot):
    bot.db.update_required_roles(GUILD_ID, [77])
    ok = make_member(user_id=10, roles=[make_role(77)])
    missing = make_member(user_id=11)
    a_bot = make_member(user_id=12)
    for m in (ok, missing):
        m.bot = False
    a_bot.bot = True
    guild.members = [ok, missing, a_bot]
    itx.followup.send.return_value = MagicMock(edit=AsyncMock())

    await cog._check_roles.callback(cog, itx)

    description = itx.channel.send.call_args.kwargs["embed"].description
    assert "<@11>" in description
    assert "<@10>" not in description
    assert "<@12>" not in description


###################
### lastmessage ###
###################


async def test_lastmessage_found(cog, ctx, member, bot):
    bot.db.add_or_update_user_log(GUILD_ID, "Test Guild", member.id, member.name, datetime.now(UTC))
    await cog._last_message.callback(cog, ctx, member)
    assert "last message on" in ctx.send.call_args.kwargs["embed"].description


async def test_lastmessage_not_found(cog, ctx, member):
    await cog._last_message.callback(cog, ctx, member)
    assert "No messages found" in ctx.send.call_args.kwargs["embed"].description


#####################
### checkinactive ###
#####################


async def test_checkinactive_finds_inactive_members(cog, itx, guild, bot, monkeypatch):
    active = make_member(user_id=20, name="active")
    stale = make_member(user_id=21, name="stale")
    never = make_member(user_id=22, name="never")
    for m in (active, stale, never):
        m.bot = False
    guild.members = [active, stale, never]
    now = datetime.now(UTC)
    bot.db.add_or_update_user_log(GUILD_ID, "Test Guild", 20, "active", now)
    bot.db.add_or_update_user_log(GUILD_ID, "Test Guild", 21, "stale", now - timedelta(days=60))

    # Capture the paginated results instead of sending a real Pagination view
    fake_pagination = MagicMock()
    fake_pagination.return_value.init = AsyncMock()
    fake_pagination.compute_total_pages = moderation.Pagination.compute_total_pages
    monkeypatch.setattr(moderation, "Pagination", fake_pagination)

    await cog._check_inactive.callback(cog, itx, 30)

    fake_pagination.return_value.init.assert_awaited_once()
    get_page = fake_pagination.call_args.args[1]
    embed, _ = get_page(1)
    names = " ".join(f.value for f in embed.fields)
    assert "stale" in names
    assert "never" in names
    assert "active" not in names


async def test_getmodroles_when_unset(cog, itx, bot):
    # Regression: get_mod_roles returns None after `/unset role mod`
    bot.db.drop_field(GUILD_ID, "mod_roles")
    await cog._get_mod_roles.callback(cog, itx)
    itx.response.send_message.assert_awaited_once_with("No mod roles set.", ephemeral=True)
