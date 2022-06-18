### Imports ###

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get

import os, shutil
from pathlib import Path
from git import Repo

from utils.helper import * 

logger = get_logger(__name__)
cog_path = Path(__file__)

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
        logger.info(f"Cog Online: {self.qualified_name}")

    @commands.command(name="get_mod_roles", description="Get a list of guild's mod roles", aliases=['modroles'])
    async def _get_mod_roles(self, ctx):
        mod_roles = self.bot.db.get_mod_roles(ctx.guild.id)
        r = []
        for i in mod_roles:
            r.append(f"<@&{i}>")
        await ctx.send(embed=discord.Embed(description=f"Mod roles: {r}."))

    @commands.command(name="getobject", description="Returns the type of an argument", aliases=['whatis'])
    async def _get_object_type(self, ctx, obj):
        objects = obj.split(" ")
        for i in objects:
            await ctx.send(f"```Object: {i}\nType: {type(i)}\n```")

    @commands.command(name="getemojis", description="Get a list of guild's emojis (Used in Glass Harbor - can be safely ignored)", aliases=['emojis'])
    async def _get_guild_emojis(self, ctx):
        # Check for mod
        mod_roles = self.bot.db.get_mod_roles(ctx.guild.id)
        if not await role_check(ctx, mod_roles):
            return

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
        await ctx.send(f"__**Guild emojis (animated):**__\n```\n{emoji_names_anim}\n```")

    @commands.command(name="download_emojis", description="Downloads a guild's emojis (Used in Glass Harbor - can be safely ignored)", aliases=['dlemojis', 'dle'])
    async def _download_emojis(self, ctx) -> None:
        # Check for mod
        mod_roles = self.bot.db.get_mod_roles(ctx.guild.id)
        if not await role_check(ctx, mod_roles):
            return

        await ctx.message.delete()
        fp = f"./downloads/{ctx.guild.name}/emojis"
        Path(fp).mkdir(parents=True, exist_ok=True)
        Path(fp, 'png').mkdir(parents=True, exist_ok=True)
        Path(fp, 'gif').mkdir(parents=True, exist_ok=True)
        guild = self.bot.get_guild(ctx.guild.id)
        count = 0
        for e in guild.emojis:
            fn = f"gif/{e.name}.gif" if e.animated else f"png/{e.name}.png"
            await e.save(fp=os.path.join(fp, fn))
            count += 1
        await ctx.send(f"{count} emoji's downloaded", delete_after=2.0)
        return

    @commands.command(name='clearfilecache', aliases=['cfc','rm -rf'])
    async def _clear_file_cache(self, ctx):
        mod_roles = self.bot.db.get_mod_roles(ctx.guild.id)
        if not await role_check(ctx, mod_roles):
            return
        shutil.rmtree(f"downloads/{ctx.guild.name}/temp")
        await ctx.message.delete()
        await ctx.send(f"File cache cleared!", delete_after=2.0)

    @commands.command(name='syncemojis', description="Clone glass' discord repo and sync Glass Harbor emojis")
    async def _sync_emoji(self, ctx):
        if ctx.guild.id != 393995277713014785:
            await ctx.send(embed=discord.Embed(description=f"Oops! This command can only be used in the Glass Harbor Discord server."))
            return
        
        repo_path = f"{cog_path.parent.parent.parent}/discord-stuff"
        if not Path(repo_path).exists:
            # clone the repo
            pass
        else:
            pass

    # Purely academic / for personal usage if you want to host your own instance. 
    # Not intended for scraping servers for content. 
    # @app_commands.command(name='download', description="Downloads all files in current channel (personal archiving tool - do not use to steal content from others")
    # async def download(self, itx: discord.Interaction):
    #     download_dir = 'some/local/path'
    #     for msg in itx.channel.history():
    #         if msg.attachments:
    #             for a in msg.attachments:
    #                 await a.save(fp=download_dir, filename=a.name)