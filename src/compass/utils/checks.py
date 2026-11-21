"""Shared permission checks for cog commands.

Usage:
    from compass.utils.checks import has_mod_ctx, has_mod_itx

    @has_mod_itx
    @app_commands.command(...)
    async def my_slash_command(self, itx: discord.Interaction): ...

    @has_mod_ctx
    @commands.command(...)
    async def my_text_command(self, ctx: commands.Context): ...
"""

import asyncio

import discord
from discord import app_commands
from discord.ext import commands


def is_mod(member: discord.Member | discord.User, mod_roles: list | None) -> bool:
    """True if member is an admin or holds one of the guild's mod roles.

    Args:
        member: The user to check. Non-members (e.g. DMs, where there is no guild) are never mods.
        mod_roles: The guild's mod role IDs. None when unset (e.g. after `/unset role mod`).
    """
    if not isinstance(member, discord.Member):
        return False
    if member.guild_permissions.administrator:
        return True
    role_ids = {r.id for r in member.roles}
    return any(int(r) in role_ids for r in mod_roles or [])


async def mod_check_itx(itx: discord.Interaction) -> bool:
    """Slash command check: allow admins and mods, otherwise reply ephemerally and deny."""
    mod_roles = itx.client.db.get_mod_roles(itx.guild_id) if itx.guild_id else None
    if is_mod(itx.user, mod_roles):
        return True
    await itx.response.send_message("You do not have permission to use this command.", ephemeral=True)
    return False


async def mod_check_ctx(ctx: commands.Context) -> bool:
    """Text command check: allow admins and mods, otherwise reply briefly, delete the command, and deny."""
    mod_roles = ctx.bot.db.get_mod_roles(ctx.guild.id) if ctx.guild else None
    if is_mod(ctx.author, mod_roles):
        return True
    await ctx.send("You do not have permission to use this command.", delete_after=5.0)
    await asyncio.sleep(3)
    await ctx.message.delete()
    return False


has_mod_itx = app_commands.check(mod_check_itx)
has_mod_ctx = commands.check(mod_check_ctx)
