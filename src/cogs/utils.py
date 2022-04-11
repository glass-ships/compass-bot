### Imports ###

import discord
from discord.ext import commands
from discord.utils import get

from typing import Optional 

from helper import * 

### Setup Cog

# Startup method
async def setup(bot):
    await bot.add_cog(Utils(bot))

# Define Class
class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.name = self.qualified_name

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Cog Online: {self.qualified_name}")

    @commands.command()
    async def get_mod_roles(self, ctx):
        mod_roles = self.bot.db.get_mod_roles(ctx.guild.id)
        r = []
        for i in mod_roles:
            r.append(f"<@&{i}>")
        await ctx.send(f"Mod roles: {r}.")        

    @commands.command(aliases=['whatis'])
    async def getobject(self, ctx, *, obj):
        objects = obj.split(" ")
        for i in objects:
            await ctx.send(f"```Object: {i}\nType: {type(i)}\n```")