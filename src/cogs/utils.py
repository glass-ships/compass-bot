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

    @commands.command(aliases=['emojis'])
    async def getallemojis(self, ctx):
        g = self.bot.get_guild(ctx.guild.id)
        emojis_static = []
        emoji_names_static = []
        emojis_anim = []
        emoji_names_anim = []
        for i in g.emojis:
            if i.animated == True:
                emojis_anim.append(i)
                emoji_names_anim.append(i.name)
            else:
                emojis_static.append(i)
                emoji_names_static.append(i.name)

        await ctx.send(f"__**Guild emojis (static):**__\n```\n{emoji_names_static}\n```")
        # emojis = [f"<:{i.name}:{i.id}>" for i in emojis_static]
        # emojis = " ".join(emojis)
        # await ctx.send(f"{emojis}")

        await ctx.send(f"__**Guild emojis (animated):**__\n```\n{emoji_names_anim}\n```")
        # emojis = [f"<a:{i.name}:{i.id}>" for i in emojis_anim]
        # emojis = " ".join(emojis)
        # await ctx.send(f"{emojis}")
    
    @commands.command(aliases=['guilds'])
    async def getallguilds(self, ctx):
        guilds = self.bot.db.get_all_guilds()
        guildlist = []
        print("Guilds:")
        for i in guilds:
            print(i)
            g = self.bot.get_guild(i)
            print(g)
            guildlist.append(f"Guild: {g} ID: {g.id} Type: {type(g)} ID Type: {type(g.id)}")
        await ctx.send(f"Compass guilds:\n{guildlist}")