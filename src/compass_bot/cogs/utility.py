import asyncio
import os
import requests
import shutil
from pathlib import Path
from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from compass_bot.utils.bot_config import COMPASS_ROOT, GLASS, GLASS_HARBOR
from compass_bot.utils.utils import get_emojis, send_embed, get_resource_repo, get_resource_path, REPO_PATH


cog_path = Path(__file__)


async def mod_check_ctx(ctx: commands.Context):
    mod_roles = bot.db.get_mod_roles(ctx.guild.id)
    user_roles = [x.id for x in ctx.author.roles]
    if ctx.author.guild_permissions.administrator:
        return True
    if any(int(i) in user_roles for i in mod_roles):
        return True
    await ctx.send("You do not have permission to use this command.", delete_after=5.0)
    await asyncio.sleep(3)
    await ctx.message.delete()
    return False


async def mod_check_itx(itx: discord.Interaction):
    mod_roles = bot.db.get_mod_roles(itx.guild_id)
    user_roles = [x.id for x in itx.user.roles]
    if itx.user.guild_permissions.administrator:
        return True
    if any(int(i) in user_roles for i in mod_roles):
        return True
    await itx.response.send_message("You do not have permission to use this command.", ephemeral=True)
    return False


has_mod_ctx = commands.check(mod_check_ctx)
has_mod_itx = app_commands.check(mod_check_itx)


async def setup(bot):
    await bot.add_cog(Utility(bot))


class Utility(commands.Cog):
    def __init__(self, bot_: commands.Bot):
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
    async def _test(self, ctx: commands.Context, channel_id: int):
        # await ctx.send("Test command")
        await ctx.send(f"Testing channel: {bot.get_channel(channel_id).jump_url}")

    @has_mod_ctx
    @commands.command(name="broadcast", aliases=["announce", "sendall"])
    async def broadcast(self, ctx: commands.Context, *, msg: str):
        if ctx.author.id != GLASS:
            return
        for server in bot.guilds:
            log_channel = bot.db.get_channel_logs(ctx.guild.id)
            if not log_channel:
                log_channel = ctx.guild.system_channel
            for channel in server.text_channels:
                try:
                    await channel.send(msg)
                except Exception:
                    continue
                else:
                    break

    @has_mod_ctx
    @commands.command(name="getcommands", aliases=["gc", "getcmds"])
    async def _get_commands(self, ctx: commands.Context, guild_id=None):
        g = bot.get_guild(int(guild_id) if guild_id else ctx.guild.id)
        global_get_cmds = bot.tree.get_commands()
        guild_get_cmds = bot.tree.get_commands(guild=g)
        guild_fetch_cmds = await bot.tree.fetch_commands(guild=g)
        global_fetch_cmds = await bot.tree.fetch_commands()

        def cmds_to_str(list):
            if not list:
                return "No commands found"
            for i in list:
                if isinstance(i, discord.app_commands.Command):
                    result = f"/{i.name}\n"
                elif isinstance(i, discord.app_commands.Group):
                    for j in i.commands:
                        result = f"/{i.name} {j.name}\n"
                else:
                    result = "No commands found"
            return result  # type: ignore

        msg = f"__**Global Commands (get) ({len(global_get_cmds)}):**__\n"
        msg += cmds_to_str(global_get_cmds)
        msg += f"__**Guild Commands (get) ({len(guild_get_cmds)}):**__\n"
        msg += cmds_to_str(guild_get_cmds)
        msg += f"__**Global Commands (fetch) ({len(global_fetch_cmds)}):**__\n"
        msg += cmds_to_str(global_fetch_cmds)
        msg += f"__**Guild Commands (fetch) ({len(guild_fetch_cmds)}):**__\n"
        msg += cmds_to_str(guild_fetch_cmds)

        await ctx.send(embed=discord.Embed(description=msg))

    @has_mod_ctx
    @commands.command(name="clearcommands", aliases=["cc"])
    async def _clear_commands(self, ctx: commands.Context, guild_id=None):
        g = bot.get_guild(int(guild_id) if guild_id else ctx.guild.id)
        bot.tree.clear_commands(guild=g)
        fmt = await bot.tree.sync(guild=g)
        await ctx.send(embed=discord.Embed(description=f"{len(fmt)} commands cleared from {g.name}"))

    ##############################
    ### Emoji/Sticker Commands ###
    ##############################

    ### Emoji Commands

    @has_mod_ctx
    @commands.command(
        name="getemojis",
        description="Get a list of guild's emojis (Used in Glass Harbor - can be safely ignored)",
        aliases=["emojis"],
    )
    async def _get_emojis(self, ctx: commands.Context):
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
    async def _download_emojis(self, ctx: commands.Context) -> None:
        get_resource_repo()
        if os.path.exists(f"{REPO_PATH}/{ctx.guild.name}/emojis"):
            fp = f"{REPO_PATH}/{ctx.guild.name}/emojis"
        else:
            fp = f"{COMPASS_ROOT}/downloads/{ctx.guild.name}/emojis"
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
    async def _sync_emojis(self, ctx: commands.Context, option: Optional[str] = None):
        await send_embed(channel=ctx.channel, description="Syncing emojis...")
        backup_dir_static = get_resource_path(ctx.guild.name, "emojis", "png")
        backup_dir_anim = get_resource_path(ctx.guild.name, "emojis", "gif")
        if not (backup_dir_static and backup_dir_anim):
            await ctx.send("**Error**: No emoji backup found.")
            return
        backup_static = os.listdir(backup_dir_static)
        backup_anim = os.listdir(backup_dir_anim)
        guild_static, guild_anim = get_emojis(bot.get_guild(ctx.guild.id))
        to_add = [f"{backup_dir_static}/{e}" for e in backup_static if e[:-4] not in [i.name for i in guild_static]] + [
            f"{backup_dir_anim}/{e}" for e in backup_anim if e[:-4] not in [i.name for i in guild_anim]
        ]
        to_remove = [e for e in guild_static if f"{e.name}.png" not in backup_static] + [
            e for e in guild_anim if f"{e.name}.gif" not in backup_anim
        ]
        if not to_add and not to_remove:
            await ctx.send(embed=discord.Embed(description="Emojis already synced!"))
            return
        await ctx.send(
            embed=discord.Embed(description=f"Adding {len(to_add)} emojis and removing {len(to_remove)} emojis")
        )
        await self._clear_emojis(ctx, to_remove)
        await self._add_emojis(ctx, to_add)
        await ctx.send(embed=discord.Embed(description="Emojis Synced!"))

    @has_mod_ctx
    @commands.command(name="clearemojis", description="Clears all emojis in a guild")
    async def _clear_emojis(self, ctx: commands.Context, emojis: List[discord.Emoji] = None) -> None:
        def _check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        to_remove = ctx.guild.emojis if emojis is None else emojis
        await send_embed(
            channel=ctx.channel,
            description=f"**Warning**: This command will delete all {len(to_remove)} emojis in this server. Proceed? (y/n)",
        )
        try:
            msg = await bot.wait_for("message", check=_check, timeout=30.0)
        except asyncio.TimeoutError:
            await send_embed(channel=ctx, description="Command timed out after 30 sec.")
            return
        if not msg.content.lower().startswith("y"):
            await send_embed(channel=ctx, description="Command cancelled.")
            return
        for e in to_remove:
            await ctx.guild.delete_emoji(e)
            await asyncio.sleep(1.0)
        await send_embed(channel=ctx, description=f"{len(to_remove)} emojis removed")
        return

    # Not a command, but a helper function for syncemojis
    async def _add_emojis(self, ctx: commands.Context, emojis: list = None) -> None:
        """Adds emojis to a guild from a list of filepaths"""
        for e in emojis:
            with open(e, "rb") as image:
                name = e.split("/")[-1]
                name = name[:-4]
                try:
                    await ctx.guild.create_custom_emoji(name=name, image=image.read())
                except Exception as error:
                    await ctx.send(f"Error uploading emoji `{e}`: {error}")
            await asyncio.sleep(1)
        await send_embed(channel=ctx.channel, description=f"{len(emojis)} emojis added")
        return

    ### Sticker Commands

    @has_mod_ctx
    @commands.command(name="getstickers", description="Get a list of guild's stickers", aliases=["stickers"])
    async def _get_stickers(self, ctx: commands.Context):
        stickers = bot.get_guild(ctx.guild.id).stickers
        await ctx.send(f"__**Guild stickers:**__\n```\n{[i.name for i in stickers]}\n```")

    @has_mod_ctx
    @commands.command(name="downloadstickers", description="Downloads a guild's stickers", aliases=["dlstickers"])
    async def _download_stickers(self, ctx: commands.Context) -> None:
        dir = get_resource_path(ctx.guild.name, "stickers")
        if not dir:
            dir = f"{COMPASS_ROOT}/downloads/{ctx.guild.name}/stickers"
            Path(dir).mkdir(parents=True, exist_ok=True)
        guild = bot.get_guild(ctx.guild.id)
        count = 0
        for s in guild.stickers:
            try:
                e = ctx.guild.get_emoji(int(s.emoji))
            except ValueError:
                e = s.emoji
            r = requests.get(s.url)
            with open(f"{dir}/{s.name}_{e}.{s.format.name}", "wb") as f:
                f.write(r.content)
            count += 1
        await send_embed(channel=ctx, description=f"{count} stickers downloaded")

    @has_mod_ctx
    @commands.command(name="syncstickers", description="Syncs stickers from resource repo or local backup")
    async def _sync_stickers(self, ctx: commands.Context, option: str = None):
        await send_embed(channel=ctx, description="Syncing stickers...")
        backup_dir = get_resource_path(ctx.guild.name, "stickers")
        if not backup_dir:
            await ctx.send("**Error**: No sticker backup found.")
            return
        backup = os.listdir(backup_dir)
        guild_stickers = bot.get_guild(ctx.guild.id).stickers
        to_add = [
            f"{backup_dir}/{e}" for e in backup if e.split(".")[0].split("_")[0] not in [i.name for i in guild_stickers]
        ]
        to_remove = [e for e in guild_stickers if f"{e.name}.{e.format.name}" not in backup]
        await self._clear_stickers(ctx, to_remove)
        await self._add_stickers(ctx, to_add)
        await ctx.send(embed=discord.Embed(description="Stickers Synced!"))

    @has_mod_ctx
    @commands.command(name="clearstickers", description="Clears all stickers in a guild")
    async def _clear_stickers(self, ctx: commands.Context, stickers: List[discord.Sticker] = None) -> None:
        def _check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        to_remove = ctx.guild.stickers if stickers is None else stickers
        await send_embed(
            channel=ctx.channel,
            description=f"**Warning**: This command will delete all {len(to_remove)} stickers in this server. Proceed? (y/n)",
        )
        try:
            msg = await bot.wait_for("message", check=_check, timeout=30.0)
        except asyncio.TimeoutError:
            await send_embed(channel=ctx, description="Command timed out after 30 sec.")
            return
        if not msg.content.lower().startswith("y"):
            await send_embed(channel=ctx, description="Command cancelled.")
            return
        to_remove = ctx.guild.stickers if stickers is None else stickers
        for s in to_remove:
            await ctx.guild.delete_sticker(s)
            await asyncio.sleep(1.0)
        await send_embed(channel=ctx, description=f"{len(to_remove)} stickers removed")
        return

    # Not a command, but a helper function for syncstickers
    async def _add_stickers(self, ctx: commands.Context, stickers: list = None) -> None:
        """Adds stickers to a guild from a list of filepaths"""
        for s in stickers:
            parts = s.split("/")[-1].split(".")[0].split("_")
            await ctx.send(f"Adding sticker `{parts}`")
            if len(parts) == 1:
                name = parts[0]
                emoji = "❓"
            else:
                name = parts[0]
                emoji = parts[1]
            try:
                emoji = ctx.guild.get_emoji(int(emoji))
            except ValueError:
                emoji = emoji
            try:
                await ctx.guild.create_sticker(
                    name=name,
                    description=f"",
                    emoji=emoji,
                    file=discord.File(s),
                )
            except Exception as error:
                await ctx.send(f"Error uploading sticker `{s}`: {error}")
            await asyncio.sleep(1)
        await send_embed(channel=ctx, description=f"{len(stickers)} stickers added")
        return

    #####################
    ### Misc Commands ###
    #####################

    @has_mod_ctx
    @commands.command(name="clearfilecache", aliases=["cfc", "rm -rf"])
    async def _clear_file_cache(self, ctx: commands.Context, option: str):
        shutil.rmtree(f"downloads/")
        await ctx.message.delete()
        await ctx.send(f"File cache cleared!", delete_after=2.0)

    # Purely academic / for personal usage if you want to host your own instance.
    # Not intended for scraping servers for content.
    @has_mod_ctx
    @commands.command(name="download", description="Downloads all attachments in a channel", aliases=["dl"])
    async def _download(self, ctx: commands.Context):
        glass_servers = [GLASS_HARBOR, 771161933301940224, 827388504232165386]
        if ctx.guild.id not in glass_servers:  # type: ignore
            await ctx.response.send_message(
                "This command is only available in the Glass Discord servers.", ephemeral=True
            )
            return
        download_dir = f"./downloads/{ctx.guild.name}/{ctx.channel.name}"  # type: ignore
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
