### Imports ###

import discord
from discord import app_commands
from discord.ext import commands
#from discord.utils import get

import os

from helper import * 
from database import *

logger = get_logger(__name__)

### Setup Cog

# Startup method
async def setup(bot):
    await bot.add_cog(Main(bot))

### Define Class
class Main(commands.Cog):
    def __init__(self, bot):
        # sets the client variable so we can use it in cogs
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")

    @app_commands.command(name="ping")
    async def ping(self, interaction: discord.Interaction):
        """Responds with "pong" and the ping latency"""
        await interaction.response.send_message(f"Pong! Latency: {round(self.bot.latency, 2)} ms", ephemeral=True)

    @app_commands.command(name="avatar")
    async def avatar(self, itx: discord.Interaction, *, user: discord.Member=None):
        """Returns a user's Discord avatar"""
        u = user or itx.user
        mem = await itx.guild.fetch_member(u.id)
        userAvatarUrl = mem.avatar.url
        embed = discord.Embed(description=f"{mem.mention}'s avatar")
        embed.set_image(url=f"{userAvatarUrl}")
        await itx.response.send_message(embed=embed)

    @app_commands.command(name="banner")
    async def banner(self, itx: discord.Interaction, *, user: discord.Member=None):
        """Returns a user's Discord banner"""
        u = user or itx.user
        mem = await self.bot.fetch_user(u.id)
        userBannerUrl = mem.banner
        embed = discord.Embed(description=f"{mem.mention}'s banner")
        embed.set_image(url=f"{userBannerUrl}")
        await itx.response.send_message(embed=embed)
