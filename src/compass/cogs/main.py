from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands

from loguru import logger

from compass.bot import CompassBot
from compass.components.pagination import Pagination
from compass.config.bot_config import COLORS


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
        cmds = [c for c in bot.walk_commands()]
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

    async def _profile_autocomplete(self, itx: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        options = ["User", "Server"]
        return [
            app_commands.Choice(name=option, value=option) for option in options if current.lower() in option.lower()
        ]

    @app_commands.command(name="avatar")
    @app_commands.autocomplete(profile=_profile_autocomplete)
    async def _avatar(self, itx: discord.Interaction, user: Optional[discord.Member] = None, profile: str = "User"):
        """Returns a user's Discord avatar"""
        await itx.response.defer()
        u = user or itx.user
        mem = await itx.guild.fetch_member(u.id)
        avatarURL = mem.avatar.url if profile == "User" else mem.guild_avatar.url
        embed = discord.Embed(description=f"{mem.mention}'s avatar")
        embed.set_image(url=f"{avatarURL}")
        await itx.followup.send(embed=embed)
        return

    @app_commands.command(name="banner")
    @app_commands.autocomplete(profile=_profile_autocomplete)
    async def _banner(self, itx: discord.Interaction, user: Optional[discord.Member] = None, profile: str = "User"):
        """Returns a user's Discord banner"""
        await itx.response.defer()

        u = user or itx.user
        # mem = await itx.guild.fetch_member(u.id)
        mem = await bot.fetch_user(u.id)
        userBannerUrl = mem.banner.url
        description = f"{mem.mention}'s banner"
        if profile == "Server":
            description += "\n(server banners are not currently supported by discord.py)"
        embed = discord.Embed(description=description)
        embed.set_image(url=f"{userBannerUrl}")
        await itx.followup.send(embed=embed)
        return
