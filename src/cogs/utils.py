### Imports ###

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get

import os, shutil, subprocess
from pathlib import Path
from git import Repo

from utils.helper import * 

logger = get_logger(__name__)
cog_path = Path(__file__)

async def _mod_check_ctx(ctx):
    mod_roles = bot.db.get_mod_roles(ctx.guild.id)
    user_roles = [x.id for x in ctx.author.roles]
    if any(i in user_roles for i in mod_roles):
        return True
    await ctx.send("You do not have permission to use this command.", delete_after=5.0)
    await asyncio.sleep(3)
    await ctx.message.delete()
    return False
async def _mod_check_itx(itx: discord.Interaction):
    mod_roles = bot.db.get_mod_roles(itx.guild_id)
    user_roles = [x.id for x in itx.user.roles]
    if any(i in user_roles for i in mod_roles):
        return True
    await itx.response.send_message("You do not have permission to use this command.", ephemeral=True)
    return False
has_mod_ctx = commands.check(_mod_check_ctx)
has_mod_itx = app_commands.check(_mod_check_itx)

### Setup Cog

# Startup method
async def setup(bot):
    await bot.add_cog(Utils(bot))

# Define Class
class Utils(commands.Cog):
    def __init__(self, bot_):
        global bot
        bot = bot_
        self.name = self.qualified_name

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")


    @commands.command(name="test")
    async def _test(self, ctx, arg: str):
        thing = arg - 3
        return thing

    @commands.command(name='clearfilecache', aliases=['cfc','rm -rf'])
    async def _clear_file_cache(self, ctx, option: str):
        mod_roles = bot.db.get_mod_roles(ctx.guild.id)
        if not await role_check(ctx, mod_roles):
            return
        shutil.rmtree(f"downloads/{ctx.guild.name}/temp")
        await ctx.message.delete()
        await ctx.send(f"File cache cleared!", delete_after=2.0)

    @commands.command(name="getemojis", description="Get a list of guild's emojis (Used in Glass Harbor - can be safely ignored)", aliases=['emojis'])
    async def _get_emojis(self, ctx):
        mod_roles = bot.db.get_mod_roles(ctx.guild.id)
        if not await role_check(ctx, mod_roles):
            return

        emojis_static, emojis_anim = get_emojis(bot.get_guild(ctx.guild.id))
        await ctx.send(f"__**Guild emojis (static):**__\n```\n{emojis_static}\n```")
        await ctx.send(f"__**Guild emojis (animated):**__\n```\n{emojis_anim}\n```")

    @has_mod_ctx
    @commands.command(name="download_emojis", description="Downloads a guild's emojis (Used in Glass Harbor - can be safely ignored)", aliases=['dlemojis', 'dle'])
    async def _download_emojis(self, ctx) -> None:
        await ctx.message.delete()
        fp = f"./downloads/{ctx.guild.name}/emojis"
        Path(fp).mkdir(parents=True, exist_ok=True)
        Path(fp, 'png').mkdir(parents=True, exist_ok=True)
        Path(fp, 'gif').mkdir(parents=True, exist_ok=True)
        guild = bot.get_guild(ctx.guild.id)
        count = 0
        for e in guild.emojis:
            fn = f"gif/{e.name}.gif" if e.animated else f"png/{e.name}.png"
            await e.save(fp=os.path.join(fp, fn))
            count += 1
        await ctx.send(f"{count} emoji's downloaded", delete_after=2.0)
        return

    @commands.command(name='syncemojis', description="Clone glass' discord repo and sync Glass Harbor emojis")
    async def _sync_emojis(self, ctx):
        if ctx.guild.id != 393995277713014785:
            await ctx.send(embed=discord.Embed(description=f"Oops! This command can only be used in the Glass Harbor Discord server."))
            return
        
        repo_url = f"https://glass-ships:{os.getenv('GITLAB_TOKEN')}@gitlab.com/glass-ships/discord-stuff.git"
        repo_path = f"{cog_path.parent.parent.parent.parent}"
        print(repo_path)
        if not Path(f"{repo_path}/discord-stuff").is_dir():
            subprocess.call(['git', 'clone', repo_url, f"{repo_path}/discord-stuff"])
        else:
            logger.debug("Repo already exists")

        local_static, local_anim = get_emojis(bot.get_guild(ctx.guild.id))

        remote_static = os.listdir(f"{repo_path}/discord-stuff/_emojis/png")
        remote_anim = os.listdir(f"{repo_path}/discord-stuff/_emojis/gif")

        print(f"Remote static emojis: {remote_static}")
        print(f"Remote animated emojis: {remote_anim}")

        print(f"Local static emojis: {local_static}")
        print(f"Local animated emojis: {local_anim}")

        # if in server but not in folder, "guild.delete_emoji()""
        # if in folder but not in server, "guild.add_emoji()""
        # maybe return a nice message

    # Purely academic / for personal usage if you want to host your own instance. 
    # Not intended for scraping servers for content. 
    @app_commands.command(name='download', description="Downloads all files in current channel (personal archiving tool - do not use to steal content from others)")
    async def _download(self, itx: discord.Interaction):
        download_dir = f"./downloads/{itx.guild.name}/{itx.channel.name}"
        count = 0
        await itx.response.defer(ephemeral=True)
        for msg in itx.channel.history():
            if msg.attachments:
                for a in msg.attachments:
                    await a.save(fp=download_dir, filename=a.name)
                    count += 1
        await itx.followup.send(f"Success: Downloaded {count} items.")