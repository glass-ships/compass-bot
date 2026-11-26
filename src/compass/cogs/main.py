import logging
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from compass.bot import CompassBot
from compass.components.pagination import Pagination
from compass.config.bot_config import COLORS

logger = logging.getLogger(__name__)

bot: CompassBot  # set in the cog's __init__ via `global bot`

Profile = Literal["User", "Server"]  # fixed slash-command choices


async def setup(bot):
    """Cog setup method"""
    await bot.add_cog(Main(bot))


class Main(commands.Cog):
    def __init__(self, bot_: CompassBot):
        global bot
        bot = bot_

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")

    @app_commands.command(name="help", description="List chat commands")
    async def help(self, itx: discord.Interaction):
        await itx.response.defer()
        cmds = list(bot.walk_commands())
        per_page = 10

        def _get_page(page: int):
            emb = discord.Embed(
                title="Commands",
                description="A list of Compass bot chat commands\n(to be used with `;command_name`)",
                color=COLORS.random(),
            )
            offset = (page - 1) * per_page
            n = Pagination.compute_total_pages(len(cmds), per_page)
            for cmd in cmds[offset : offset + per_page]:
                emb.add_field(name=f"{cmd.name} {cmd.aliases}", value=cmd.description, inline=False)
            emb.set_author(name=f"Requested by {itx.user}")
            emb.set_footer(text=f"Page {page} of {n}")
            return emb, n

        await Pagination(itx, _get_page).init()

    @app_commands.command(name="ping")
    async def _ping(self, itx: discord.Interaction):
        """Responds with "pong" and the ping latency"""
        await itx.response.defer(ephemeral=True)
        await itx.followup.send(f"Pong! Latency: {round(bot.latency, 2)} ms", ephemeral=True)
        return

    @app_commands.command(name="avatar")
    @app_commands.describe(profile="User: their Discord avatar. Server: their avatar in this server")
    async def _avatar(self, itx: discord.Interaction, user: discord.Member | None = None, profile: Profile = "User"):
        """Returns a user's Discord avatar"""
        await itx.response.defer()
        mem = await itx.guild.fetch_member((user or itx.user).id)
        # .avatar / .guild_avatar are None when not set; default_avatar is Discord's generated one
        avatar = mem.avatar or mem.default_avatar
        description = f"{mem.mention}'s avatar"
        if profile == "Server":
            if mem.guild_avatar:
                avatar = mem.guild_avatar
                description = f"{mem.mention}'s server avatar"
            else:
                description += " (they have no server avatar)"
        embed = discord.Embed(description=description)
        embed.set_image(url=avatar.url)
        await itx.followup.send(embed=embed)

    @app_commands.command(name="banner")
    @app_commands.describe(profile="User: their Discord banner. Server: their banner in this server")
    async def _banner(self, itx: discord.Interaction, user: discord.Member | None = None, profile: Profile = "User"):
        """Returns a user's Discord banner"""
        await itx.response.defer()
        u = user or itx.user
        banner = None
        description = f"{u.mention}'s banner"
        if profile == "Server":
            banner = (await itx.guild.fetch_member(u.id)).guild_banner
            if banner:
                description = f"{u.mention}'s server banner"
            else:
                description += " (they have no server banner)"
        if banner is None:
            banner = (await bot.fetch_user(u.id)).banner  # only included when the user is fetched
        if banner is None:  # most users have no banner
            await itx.followup.send(f"{u.mention} doesn't have a banner.")
            return
        embed = discord.Embed(description=description)
        embed.set_image(url=banner.url)
        await itx.followup.send(embed=embed)
