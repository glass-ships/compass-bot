"""Tests for compass.utils.checks (shared mod permission checks)."""

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from compass.utils import checks
from compass.utils.checks import is_mod, mod_check_ctx, mod_check_itx
from tests.conftest import GUILD_ID, MOD_ROLE_ID, make_member, make_role


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(checks.asyncio, "sleep", AsyncMock())


##############
### is_mod ###
##############


@pytest.mark.parametrize(
    "member, mod_roles, expected",
    [
        pytest.param(make_member(roles=[make_role(MOD_ROLE_ID)]), [MOD_ROLE_ID], True, id="mod"),
        pytest.param(make_member(roles=[make_role(MOD_ROLE_ID)]), [str(MOD_ROLE_ID)], True, id="mod, str role ids"),
        pytest.param(make_member(admin=True), [], True, id="admin, no mod roles"),
        pytest.param(make_member(admin=True), None, True, id="admin, mod roles unset"),
        pytest.param(make_member(roles=[make_role(1)]), [MOD_ROLE_ID], False, id="regular member"),
        pytest.param(make_member(roles=[make_role(MOD_ROLE_ID)]), None, False, id="mod roles unset"),
        pytest.param(make_member(roles=[make_role(MOD_ROLE_ID)]), [], False, id="mod roles empty"),
        pytest.param(MagicMock(spec=discord.User), [MOD_ROLE_ID], False, id="DM user (not a Member)"),
    ],
)
def test_is_mod(member, mod_roles, expected):
    assert is_mod(member, mod_roles) is expected


#####################
### mod_check_itx ###
#####################


async def test_mod_check_itx_allows_mod(itx, mod_member):
    itx.user = mod_member
    assert await mod_check_itx(itx) is True
    itx.response.send_message.assert_not_awaited()


async def test_mod_check_itx_denies_and_replies(itx, member):
    itx.user = member
    assert await mod_check_itx(itx) is False
    itx.response.send_message.assert_awaited_once()
    assert itx.response.send_message.call_args.kwargs["ephemeral"] is True


async def test_mod_check_itx_mod_roles_unset(itx, mod_member, bot):
    # Regression: after `/unset role mod`, get_mod_roles returns None and the check crashed iterating it
    bot.db.drop_field(GUILD_ID, "mod_roles")
    itx.user = mod_member
    assert await mod_check_itx(itx) is False


async def test_mod_check_itx_in_dm(itx):
    itx.guild_id = None
    itx.user = MagicMock(spec=discord.User)
    assert await mod_check_itx(itx) is False


#####################
### mod_check_ctx ###
#####################


async def test_mod_check_ctx_allows_mod(ctx, mod_member):
    ctx.author = mod_member
    assert await mod_check_ctx(ctx) is True
    ctx.send.assert_not_awaited()


async def test_mod_check_ctx_denies_and_cleans_up(ctx, member):
    ctx.author = member
    assert await mod_check_ctx(ctx) is False
    ctx.send.assert_awaited_once()
    ctx.message.delete.assert_awaited_once()


async def test_mod_check_ctx_mod_roles_unset(ctx, mod_member, bot):
    bot.db.drop_field(GUILD_ID, "mod_roles")
    ctx.author = mod_member
    assert await mod_check_ctx(ctx) is False


async def test_mod_check_ctx_in_dm(ctx):
    ctx.guild = None
    ctx.author = MagicMock(spec=discord.User)
    assert await mod_check_ctx(ctx) is False
    ctx.send.assert_awaited_once()
    # Regression: deleting the user's message in a DM raises Forbidden, which surfaced as a traceback embed
    ctx.message.delete.assert_not_awaited()
