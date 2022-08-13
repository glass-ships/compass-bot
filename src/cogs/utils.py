### Imports ###

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get

import os, shutil, subprocess
from pathlib import Path
from git import Repo
from typing import Union, Literal

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

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")


    @commands.command(name="test")
    async def _test(self, ctx):
        pass

    @commands.command(name='getcommands', aliases=['gc', 'getcmds'])
    async def _get_commands(self, ctx, guild_id = None):
        g = bot.get_guild(int(guild_id) if guild_id else ctx.guild.id)
        global_get_cmds = bot.tree.get_commands()
        guild_get_cmds = bot.tree.get_commands(guild=g)
        guild_fetch_cmds = await bot.tree.fetch_commands(guild=g)
        global_fetch_cmds = await bot.tree.fetch_commands()

        def cmds_to_str(string, list):
            for i in list:
                if isinstance(i, discord.app_commands.Command):
                    string += f"/{i.name}\n"
                elif isinstance(i, discord.app_commands.Group):
                    for j in i.commands:
                        string += f'/{i.name} {j.name}\n'
            return string

        msg = f"__**Global Commands (get) ({len(global_get_cmds)}):**__\n"
        msg = cmds_to_str(msg, global_get_cmds)
        msg += f"__**Guild Commands (get) ({len(guild_get_cmds)}):**__\n"
        msg = cmds_to_str(msg, guild_get_cmds)
        msg += f"__**Global Commands (fetch) ({len(global_fetch_cmds)}):**__\n"
        msg = cmds_to_str(msg, global_fetch_cmds)
        msg += f"__**Guild Commands (fetch) ({len(guild_fetch_cmds)}):**__\n"
        msg = cmds_to_str(msg, guild_fetch_cmds)

        await ctx.send(embed=discord.Embed(description=msg))

    @commands.command(name='clearcommands', aliases=['cc'])
    async def _clear_commands(self, ctx, guild_id = None):
        g = bot.get_guild(int(guild_id) if guild_id else ctx.guild.id)
        bot.tree.clear_commands(guild=g)
        fmt = await bot.tree.sync(guild=g)
        await ctx.send(embed=discord.Embed(description=f"{len(fmt)} commands cleared from {g.name}"))

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

        emojis_static, emojis_anim = get_emojis(guild=bot.get_guild(ctx.guild.id))
        emojis_anim = [i.name for i in emojis_anim]
        emojis_static = [i.name for i in emojis_static]
        await ctx.send(f"__**Guild emojis (static):**__\n```\n{emojis_static}\n```")
        await ctx.send(f"__**Guild emojis (animated):**__\n```\n{emojis_anim}\n```")

    @has_mod_ctx
    @commands.command(name="download_emojis", description="Downloads a guild's emojis (Used in Glass Harbor - can be safely ignored)", aliases=['dlemojis', 'dle'])
    async def _download_emojis(self, ctx) -> None:
        # if ctx.guild.id != 393995277713014785:
        #     await ctx.send(embed=discord.Embed(description=f"Oops! This command can only be used in the Glass Harbor Discord server."))
        #     return
        # mod_roles = bot.db.get_mod_roles(ctx.guild.id)
        # if not await role_check(ctx, mod_roles):
        #     return
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
        # mod_roles = bot.db.get_mod_roles(ctx.guild.id)
        # if not await role_check(ctx, mod_roles):
        #     return        
        repo_url = f"https://glass-ships:{os.getenv('GITLAB_TOKEN')}@gitlab.com/glass-ships/discord-stuff.git"
        repo_path = f"{cog_path.parent.parent.parent.parent}"

        if not Path(f"{repo_path}/discord-stuff").is_dir():
            subprocess.call(['git', 'clone', repo_url, f"{repo_path}/discord-stuff"])
        else:
            logger.debug("Repo already exists")

        guild_static, guild_anim = get_emojis(bot.get_guild(ctx.guild.id))

        backup_static = os.listdir(f"{repo_path}/discord-stuff/_emojis/png")
        backup_anim = os.listdir(f"{repo_path}/discord-stuff/_emojis/gif")

        print(f"backup static emojis: {backup_static}")
        print(f"backup animated emojis: {backup_anim}")

        print(f"guild static emojis: {guild_static}")
        print(f"guild animated emojis: {guild_anim}")

        print("\nStatic - In guild, but not in repo:\n")
        for e in guild_static:
            if f'{e.name}.png' not in backup_static:
                print(f'{e.name}.png')
                #await ctx.guild.delete_emoji(e)
        # print("\nAnimated - In guild, but not in repo:\n")
        # for e in guild_anim:
        #     if f'{e.name}.gif' not in backup_anim:
        #         print(e.name)
        #         #await ctx.guild.delete_emoji(e)
        # print("\nStatic - In repo, but not in guild:\n")
        # for e in backup_static:
        #     if e not in [i.name for i in guild_static]:
        #         print(e)
        #         #with open(f"{repo_path}/discord-stuff/_emojis/png/e"):
        #         #    await ctx.guild.create_custom_emoji()
        # print("\nAnimated - In repo, but not in guild:\n")
        # for e in backup_anim:
        #     if e.name not in [i.name for i in guild_anim]:
        #         print(e)
        #         #await ctx.guild.delete_emoji(e)

        # Return a nice message

    # Purely academic / for personal usage if you want to host your own instance. 
    # Not intended for scraping servers for content. 
    @app_commands.command(name='download', description="Downloads all files in current channel (personal archiving tool)")
    async def _download(self, itx: discord.Interaction):
        download_dir = f"./downloads/{itx.guild.name}/{itx.channel.name}"
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        count = 0
        await itx.response.defer(ephemeral=True)
        async for msg in itx.channel.history():
            if msg.attachments:
                print("attachment(s) found")
                for a in msg.attachments:
                    try:
                        await a.save(fp=f"{download_dir}/{a.filename}")
                    except Exception as e:
                        await itx.followup.send(f"Error downloading attachment from {msg.id}:\n```\n{e}\n```", ephemeral=True)
                    count += 1
        await itx.followup.send(f"Success: Downloaded {count} items.", ephemeral=True)