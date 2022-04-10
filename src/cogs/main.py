### Imports ###

import discord
from discord import app_commands
from discord.ext import commands
#from discord.utils import get

import os

from helper import * 
from database import *

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
        print(f"Cog Online: {self.qualified_name}")

    @app_commands.command(name="test2")
    async def test2(self, interaction: discord.Interaction):
        """Test slash command 2"""
        response = 'Testing 2!'
        await interaction.response.send_message(response, ephemeral=True)
        #await interaction.delete_original_message()
    
    @commands.command(name="ping")
    async def ping(self, ctx):
        """
        Responds with "pong"
        Tests that the bot is connected and listening.
        """
        await ctx.send(f"Pong! Latency: {round(self.bot.latency, 1)} ms")#, delete_after=3.0)
        await asyncio.sleep(2.0)
        #await ctx.message.delete()


    @commands.command(name="avatar", aliases=['av'])
    async def avatar(self, ctx, *, user: discord.Member=None):
        """
        Returns a user's Discord avatar
        if a user is mentioned, or self if not.
        """
        if not user:
            u = ctx.author
        else:
            u = user
        mem = await ctx.guild.fetch_member(u.id)
        userAvatarUrl = mem.avatar.url
        embed = discord.Embed(description=f"{mem.mention}'s avatar")
        embed.set_image(url=f"{userAvatarUrl}")
        await ctx.send(embed=embed)
        await asyncio.sleep(3.0)
        await ctx.message.delete()


    @commands.command(name="banner", aliases=['b'])
    async def banner(self, ctx, *, user: discord.Member=None):
        """
        Returns a user's Discord banner
        if a user is mentioned, or self if not.
        """
        if not user:
            u = ctx.author
        else:
            u = user
        mem = await self.bot.fetch_user(u.id)
        userBannerUrl = mem.banner
        embed = discord.Embed(description=f"{mem.mention}'s banner")
        embed.set_image(url=f"{userBannerUrl}")
        await ctx.send(embed=embed)
        await asyncio.sleep(3.0)
        await ctx.message.delete()
