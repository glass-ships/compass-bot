import asyncio
import os
import shutil
import subprocess
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from compass_bot.utils.bot_config import GuildData, COMPASS_ROOT, GLASS_HARBOR
from compass_bot.utils.utils import get_emojis, send_embed


cog_path = Path(__file__)


async def mod_check_ctx(ctx):
    mod_roles = bot.db.get_mod_roles(ctx.guild.id)
    user_roles = [x.id for x in ctx.author.roles]
    if any(i in user_roles for i in mod_roles):
        return True
    await ctx.send("You do not have permission to use this command.", delete_after=5.0)
    await asyncio.sleep(3)
    await ctx.message.delete()
    return False


async def mod_check_itx(itx: discord.Interaction):
    mod_roles = bot.db.get_mod_roles(itx.guild_id)
    user_roles = [x.id for x in itx.user.roles]
    if any(i in user_roles for i in mod_roles):
        return True
    await itx.response.send_message("You do not have permission to use this command.", ephemeral=True)
    return False


has_mod_ctx = commands.check(mod_check_ctx)
has_mod_itx = app_commands.check(mod_check_itx)


async def setup(bot):
    await bot.add_cog(Utils(bot))


class Utils(commands.Cog):
    def __init__(self, bot_):
        global bot
        bot = bot_

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")

    ######################
    ### Debug Commands ###
    ######################

    @has_mod_ctx
    @commands.command(name="test")
    async def _test(self, ctx):
        pass

    @has_mod_ctx
    @commands.command(name="getcommands", aliases=["gc", "getcmds"])
    async def _get_commands(self, ctx, guild_id=None):
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
                        string += f"/{i.name} {j.name}\n"
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

    @has_mod_ctx
    @commands.command(name="clearcommands", aliases=["cc"])
    async def _clear_commands(self, ctx, guild_id=None):
        g = bot.get_guild(int(guild_id) if guild_id else ctx.guild.id)
        bot.tree.clear_commands(guild=g)
        fmt = await bot.tree.sync(guild=g)
        await ctx.send(embed=discord.Embed(description=f"{len(fmt)} commands cleared from {g.name}"))

    ######################
    ### Emoji Commands ###
    ######################

    @has_mod_ctx
    @commands.command(
        name="getemojis",
        description="Get a list of guild's emojis (Used in Glass Harbor - can be safely ignored)",
        aliases=["emojis"],
    )
    async def _get_emojis(self, ctx):
        emojis_static, emojis_anim = get_emojis(guild=bot.get_guild(ctx.guild.id))
        emojis_anim = [i.name for i in emojis_anim]
        emojis_static = [i.name for i in emojis_static]
        await ctx.send(f"__**Guild emojis (static):**__\n```\n{emojis_static}\n```")
        await ctx.send(f"__**Guild emojis (animated):**__\n```\n{emojis_anim}\n```")

    @has_mod_ctx
    @commands.command(
        name="download_emojis",
        description="Downloads a guild's emojis (Used in Glass Harbor - can be safely ignored)",
        aliases=["dlemojis", "dle"],
    )
    async def _download_emojis(self, ctx) -> None:
        await ctx.message.delete()
        fp = f"./downloads/{ctx.guild.name}/emojis"
        Path(fp).mkdir(parents=True, exist_ok=True)
        Path(fp, "png").mkdir(parents=True, exist_ok=True)
        Path(fp, "gif").mkdir(parents=True, exist_ok=True)
        guild = bot.get_guild(ctx.guild.id)
        count = 0
        for e in guild.emojis:
            fn = f"gif/{e.name}.gif" if e.animated else f"png/{e.name}.png"
            await e.save(fp=os.path.join(fp, fn))
            count += 1
        await ctx.send(f"{count} emoji's downloaded")  # , delete_after=2.0)
        return

    @has_mod_ctx
    @commands.command(name="syncemojis", description="Syncs emojis from resource repo or local backup")
    async def _sync_emojis(self, ctx, option: str = None):
        await send_embed(channel=ctx, description="Syncing emojis...")
        guild_static, guild_anim = get_emojis(bot.get_guild(ctx.guild.id))

        # Check for / clone resource repo
        repo_url = f"https://glass-ships:{os.getenv('GITLAB_TOKEN')}@gitlab.com/glass-ships/discord-stuff.git"
        repo_path = f"{COMPASS_ROOT.parent.parent}"
        if not Path(f"{repo_path}/discord-stuff").is_dir():
            subprocess.call(["git", "clone", repo_url, f"{repo_path}/discord-stuff"])
        else:
            subprocess.Popen(["git", "pull"], cwd=f"{repo_path}/discord-stuff")
            await asyncio.sleep(7)
            logger.debug("Repo already exists - pulling repo")

        # Check for local backup, else try repo
        local_dir = f"{COMPASS_ROOT.parent.parent}/downloads/{ctx.guild.name}/emojis"
        local_static_dir = os.listdir(f"{local_dir}/png")
        local_anim_dir = os.listdir(f"{local_dir}/gif")
        if (os.path.exists(local_dir)) and (len(local_static_dir) > 0 or len(local_anim_dir) > 0):
            backup_dir = local_dir
            backup_static = local_static_dir
            backup_anim = local_anim_dir
        else:
            backup_dir = f"{repo_path}/discord-stuff/{ctx.guild.name}/emojis"
            backup_static = os.listdir(f"{backup_dir}/png")
            backup_anim = os.listdir(f"{backup_dir}/gif")

        added = []
        removed = []
        for e in guild_static:
            if f"{e.name}.png" not in backup_static:
                removed.append(e)
        for e in guild_anim:
            if f"{e.name}.gif" not in backup_anim:
                removed.append(e)
        await self._clear_emojis(ctx, removed)
        await asyncio.sleep(3.0)

        for e in backup_static:
            if e[:-4] not in [i.name for i in guild_static]:
                added.append(f"{backup_dir}/png/{e}")
        for e in backup_anim:
            if e[:-4] not in [i.name for i in guild_anim]:
                added.append(f"{backup_dir}/gif/{e}")
        await self._add_emojis(ctx, added)

        await ctx.send(embed=discord.Embed(description="Emojis Synced!"))

    @has_mod_ctx
    @commands.command(name="clearemojis", description="Clears all emojis in a guild")
    async def _clear_emojis(self, ctx, emojis=None) -> None:
        await send_embed(
            channel=ctx.channel,
            description="Warning: This command will delete all emojis in this server. Proceed? (y/n)",
        )

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("Command timed out.")
            return
        if not msg.content.lower().startswith("y"):
            await send_embed(channel=ctx, description="Command cancelled.")
            return

        if emojis is None:
            guild_static, guild_anim = get_emojis(bot.get_guild(ctx.guild.id))
            for i in guild_static:
                await ctx.guild.delete_emoji(i)
                await asyncio.sleep(3.0)
            for i in guild_anim:
                await ctx.guild.delete_emoji(i)
                await asyncio.sleep(3.0)
            await ctx.send("All emojis removed")
        elif isinstance(emojis, list):
            for e in emojis:
                await ctx.guild.delete_emoji(e)
                await asyncio.sleep(3.0)
            await send_embed(channel=ctx, description=f"{len(emojis)} emojis removed")
        else:
            await ctx.send("Error: expected None or List[emoji names] as argument")
        return

    # Not a command, but a helper function for syncemojis
    async def _add_emojis(self, ctx, emojis: list = None) -> None:
        """Adds emojis to a guild from a list of filepaths"""
        for e in emojis:
            with open(e, "rb") as image:
                name = e.split("/")[-1]
                name = name[:-4]
                try:
                    await ctx.guild.create_custom_emoji(name=name, image=image.read())
                except Exception as error:
                    await ctx.send(f"Error uploading emoji `{e}`: {error}")
            await asyncio.sleep(3.0)
        await send_embed(channel=ctx, description=f"{len(emojis)} emojis added")
        return

    #####################
    ### Misc Commands ###
    #####################

    @has_mod_ctx
    @commands.command(name="clearfilecache", aliases=["cfc", "rm -rf"])
    async def _clear_file_cache(self, ctx, option: str):
        shutil.rmtree(f"downloads/")
        await ctx.message.delete()
        await ctx.send(f"File cache cleared!", delete_after=2.0)

    # Purely academic / for personal usage if you want to host your own instance.
    # Not intended for scraping servers for content.
    @has_mod_ctx
    @commands.command(name="download", description="Downloads all attachments in a channel", aliases=["dl"])
    async def _download(self, ctx: commands.Context):
        glass_servers = [GLASS_HARBOR, 771161933301940224, 827388504232165386]
        if ctx.guild.id not in glass_servers:
            await ctx.response.send_message(
                "This command is only available in the Glass Discord servers.", ephemeral=True
            )
            return
        download_dir = f"./downloads/{ctx.guild.name}/{ctx.channel.name}"
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        count = 0
        async for msg in ctx.channel.history():
            if msg.attachments:
                logger.debug("attachment(s) found")
                for a in msg.attachments:
                    try:
                        await a.save(fp=f"{download_dir}/{a.filename}")
                    except Exception as e:
                        await ctx.send(f"Error downloading attachment from {msg.id}:\n```\n{e}\n```")
                    count += 1
        await ctx.send(f"Success: Downloaded {count} items.")
        return
