import asyncio
import logging
import os
import shutil
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from compass.bot import CompassBot
from compass.config.bot_config import DOWNLOADS_DIR, GLASS, SERVERS
from compass.utils import get_resource_path
from compass.utils.checks import has_mod_ctx
from compass.utils.command_utils import get_emojis, send_embed, send_embed_long

logger = logging.getLogger(__name__)

bot: CompassBot  # set in the cog's __init__ via `global bot`
cog_path = Path(__file__)


async def setup(bot):
    await bot.add_cog(Utility(bot))


### Helpers


def cmds_to_str(cmds: list) -> str:
    if not cmds:
        return "No commands found"
    lines = []
    for c in cmds:
        if isinstance(c, app_commands.Group):  # local group: walk nested subcommands
            lines += [f"/{sub.qualified_name}" for sub in c.walk_commands() if isinstance(sub, app_commands.Command)]
        elif isinstance(c, app_commands.AppCommand):  # fetched from Discord
            subs = [o for o in c.options if isinstance(o, app_commands.AppCommandGroup)]
            lines += [f"/{c.name} {s.name}" for s in subs] or [f"/{c.name}"]
        else:  # local Command or ContextMenu
            lines.append(f"/{c.name}")
    return "\n".join(lines)


def sticker_filename(name: str, emoji: str, fmt: str) -> str:
    """Backup filename for a sticker: `{name}_{emoji}.{fmt}`. The emoji is kept so the sticker can be re-created.

    `emoji` is the raw `GuildSticker.emoji` (Discord's `tags`: a unicode emoji, a name, or a custom emoji ID), which
    `create_sticker` accepts back as is. Don't resolve IDs to `Emoji`: `str(Emoji)` is `<:name:id>`, invalid on Windows.
    """
    return f"{name}_{emoji}.{fmt}"


def parse_sticker_filename(filename: str) -> tuple[str, str | None]:
    """Splits a sticker backup filename into `(name, emoji)`; emoji is None if the file has none (e.g. `who me.png`).

    Splits on the first `_`: emoji tags can contain underscores (`stuck_out_tongue_winking_eye`), sticker names
    in the backups don't.
    """
    name, _, emoji = Path(filename).stem.partition("_")
    return name, emoji or None


class Utility(commands.Cog):
    def __init__(self, bot_: CompassBot):
        global bot
        bot = bot_

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")

    ######################
    ### Debug Commands ###
    ######################

    @has_mod_ctx
    @commands.command(name="test", description="Test command - unused.")
    async def _test(self, ctx: commands.Context):
        pass

    @has_mod_ctx
    @commands.command(
        name="clean_activity_log", aliases=["clract"], description="Delete entries for users not in the guild anymore"
    )
    async def _clean_activity_log(self, ctx: commands.Context):
        for guild in bot.guilds:
            await ctx.send(f"Clearing user activity in {guild.name}")
            for member in guild.members:
                user_log = bot.db.get_user_log(guild.id, member.id)
                if user_log is not None:
                    await ctx.send(f"Removing user log for {member.name}")
                    bot.db.drop_user_log(guild.id, member.id)
        await ctx.send("Activity log cleaned")

    @has_mod_ctx
    @commands.command(name="getcommands", aliases=["gc", "getcmds"], description="List all app commands (debug)")
    async def _get_commands(self, ctx: commands.Context, guild_id=None):
        g = bot.get_guild(int(guild_id) if guild_id else ctx.guild.id)
        global_get_cmds = bot.tree.get_commands()
        guild_get_cmds = bot.tree.get_commands(guild=g)
        guild_fetch_cmds = await bot.tree.fetch_commands(guild=g)
        global_fetch_cmds = await bot.tree.fetch_commands()

        msg = f"__**Global Commands (get) ({len(global_get_cmds)}):**__\n"
        msg += cmds_to_str(global_get_cmds)
        msg += f"\n__**Guild Commands (get) ({len(guild_get_cmds)}):**__\n"
        msg += cmds_to_str(guild_get_cmds)
        msg += f"\n__**Global Commands (fetch) ({len(global_fetch_cmds)}):**__\n"
        msg += cmds_to_str(global_fetch_cmds)
        msg += f"\n__**Guild Commands (fetch) ({len(guild_fetch_cmds)}):**__\n"
        msg += cmds_to_str(guild_fetch_cmds)

        await send_embed_long(channel=ctx.channel, description=msg)

    @has_mod_ctx
    @commands.command(
        name="broadcast", aliases=["announce", "sendall"], description="Broadcast a message to all servers."
    )
    async def broadcast(self, ctx: commands.Context, *, msg: str):
        if ctx.author.id != GLASS:
            return
        sent, skipped = 0, []
        for guild in bot.guilds:
            log_channel = bot.db.get_channel_logs(guild.id)
            channel = bot.get_channel(log_channel) if log_channel else None
            if channel is None:  # no log channel set, or it was deleted
                skipped.append(guild.name)
                continue
            try:
                await channel.send(msg)
                sent += 1
            except discord.HTTPException as e:  # e.g. missing permissions - don't stop the other servers
                logger.warning(f"Broadcast to {guild.name} ({guild.id}) failed: {e}")
                skipped.append(guild.name)
        summary = f"Broadcast sent to {sent}/{len(bot.guilds)} servers."
        if skipped:
            summary += f"\nSkipped: {', '.join(skipped)}"
        await ctx.send(embed=discord.Embed(description=summary))

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
        name="downloademojis",
        description="Downloads a guild's emojis (Used in Glass Harbor - can be safely ignored)",
        aliases=["dlemojis", "dle"],
    )
    async def _download_emojis(self, ctx: commands.Context) -> None:
        _dir = get_resource_path(ctx.guild.name, "emojis")
        if not _dir:
            _dir = DOWNLOADS_DIR / ctx.guild.name / "emojis"
        Path(_dir, "static").mkdir(parents=True, exist_ok=True)
        Path(_dir, "animated").mkdir(parents=True, exist_ok=True)
        guild = bot.get_guild(ctx.guild.id)
        count = 0
        for e in guild.emojis:
            fn = f"animated/{e.name}.gif" if e.animated else f"static/{e.name}.png"
            await e.save(fp=os.path.join(_dir, fn))
            count += 1
        await ctx.send(f"{count} emoji's downloaded")
        return

    @has_mod_ctx
    @commands.command(name="syncemojis", description="Syncs emojis from resource repo or local backup")
    async def _sync_emojis(self, ctx: commands.Context):
        await send_embed(channel=ctx.channel, description="Syncing emojis...")
        backup_dir_static = get_resource_path(ctx.guild.name, "emojis", "static")
        backup_dir_anim = get_resource_path(ctx.guild.name, "emojis", "animated")
        if not (backup_dir_static and backup_dir_anim):
            await ctx.send("**Error**: No emoji backup found.")
            return
        backup_static = os.listdir(backup_dir_static)
        backup_anim = os.listdir(backup_dir_anim)
        guild_static, guild_anim = get_emojis(bot.get_guild(ctx.guild.id))
        static_names = {Path(f).stem for f in backup_static}
        anim_names = {Path(f).stem for f in backup_anim}
        guild_static_names = {e.name for e in guild_static}
        guild_anim_names = {e.name for e in guild_anim}
        to_add = [f"{backup_dir_static}/{f}" for f in backup_static if Path(f).stem not in guild_static_names] + [
            f"{backup_dir_anim}/{f}" for f in backup_anim if Path(f).stem not in guild_anim_names
        ]
        to_remove = [e for e in guild_static if e.name not in static_names] + [
            e for e in guild_anim if e.name not in anim_names
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
    @commands.command(name="clearemojis", description="Removes emojis in a guild")
    async def _clear_emojis(self, ctx: commands.Context, emojis: list[discord.Emoji] = None) -> None:
        def _check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        to_remove = ctx.guild.emojis if emojis is None else emojis
        if len(to_remove) == 0:
            await send_embed(channel=ctx.channel, description="No emojis to remove.")
            return

        await send_embed(
            channel=ctx.channel,
            description=f"**Warning**: This will delete {len(to_remove)} emojis in this server. Proceed? (y/n)",
        )
        try:
            msg = await bot.wait_for("message", check=_check, timeout=30.0)
        except TimeoutError:
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
                name = Path(e).stem
                try:
                    await ctx.guild.create_custom_emoji(name=name, image=image.read())
                except Exception as error:  # noqa: BLE001 - TODO: Fix later
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
        _dir = get_resource_path(ctx.guild.name, "stickers")
        if not _dir:
            _dir = DOWNLOADS_DIR / ctx.guild.name / "stickers"
            Path(_dir).mkdir(parents=True, exist_ok=True)
        guild = bot.get_guild(ctx.guild.id)
        count = 0
        for s in guild.stickers:
            try:
                await s.save(f"{_dir}/{sticker_filename(s.name, s.emoji, s.format.name)}")
            except TypeError:  # discord.py can't download lottie stickers
                await ctx.send(f"Skipped `{s.name}`: lottie stickers can't be downloaded.")
                continue
            count += 1
        await send_embed(channel=ctx, description=f"{count} stickers downloaded")

    @has_mod_ctx
    @commands.command(name="syncstickers", description="Syncs stickers from resource repo or local backup")
    async def _sync_stickers(self, ctx: commands.Context):
        await send_embed(channel=ctx, description="Syncing stickers...")
        backup_dir = get_resource_path(ctx.guild.name, "stickers")
        if not backup_dir:
            await ctx.send("**Error**: No sticker backup found.")
            return
        backup = os.listdir(backup_dir)
        guild_stickers = bot.get_guild(ctx.guild.id).stickers
        # Compare by name only; the emoji in the filename is just for re-creating the sticker
        backup_names = {parse_sticker_filename(f)[0] for f in backup}
        guild_names = {s.name for s in guild_stickers}
        to_add = [f"{backup_dir}/{f}" for f in backup if parse_sticker_filename(f)[0] not in guild_names]
        to_remove = [s for s in guild_stickers if s.name not in backup_names]
        await self._clear_stickers(ctx, to_remove)
        await self._add_stickers(ctx, to_add)
        await ctx.send(embed=discord.Embed(description="Stickers Synced!"))

    @has_mod_ctx
    @commands.command(name="clearstickers", description="Removes stickers in a guild")
    async def _clear_stickers(self, ctx: commands.Context, stickers: list[discord.Sticker] = None) -> None:
        def _check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        to_remove = ctx.guild.stickers if stickers is None else stickers
        if len(to_remove) == 0:
            await send_embed(channel=ctx.channel, description="No stickers to remove.")
            return

        await send_embed(
            channel=ctx.channel,
            description=f"**Warning**: This will delete {len(to_remove)} stickers in this server. Proceed? (y/n)",
        )
        try:
            msg = await bot.wait_for("message", check=_check, timeout=30.0)
        except TimeoutError:
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
    async def _add_stickers(self, ctx: commands.Context, stickers: list) -> None:
        """Adds stickers to a guild from a list of filepaths"""
        for s in stickers:
            name, emoji = parse_sticker_filename(s)
            emoji = emoji or "❓"
            await ctx.send(f"Adding sticker `{name}` ({emoji})")
            try:
                await ctx.guild.create_sticker(
                    name=name,
                    description="",
                    emoji=emoji,
                    file=discord.File(s),
                )
            except Exception as error:  # noqa: BLE001 - TODO: Fix later
                await ctx.send(f"Error uploading sticker `{s}`: {error}")
            await asyncio.sleep(1)
        await send_embed(channel=ctx, description=f"{len(stickers)} stickers added")
        return

    #####################
    ### Misc Commands ###
    #####################

    @has_mod_ctx
    @commands.command(name="resources", description="Prints the resource path for the current guild")
    async def _resources(self, ctx: commands.Context):
        await ctx.send(f"Resource path for {ctx.guild.name}: `{get_resource_path(ctx.guild.name)}`")

    @has_mod_ctx
    @commands.command(name="cleardownloads", aliases=["clr", "rm -rf"], description="Clear locally downloaded files")
    async def _clear_downloads(self, ctx: commands.Context):
        await ctx.message.delete()
        if not DOWNLOADS_DIR.exists():
            await ctx.send("Nothing to clear.", delete_after=2.0)
            return
        shutil.rmtree(DOWNLOADS_DIR)
        await ctx.send("Downloads cleared!", delete_after=2.0)

    # Purely academic / for personal usage if you want to host your own instance.
    # Not intended for scraping servers for content.
    @has_mod_ctx
    @commands.command(name="download", description="Downloads all attachments in a channel", aliases=["dl"])
    async def _download(self, ctx: commands.Context):
        glass_servers = [SERVERS.GLASS_HARBOR, SERVERS.GLASS_TEST, SERVERS.GLASS_H]
        if ctx.guild.id not in glass_servers:
            await ctx.send("This command is only available in Glass Discord servers.")
            return
        download_dir = DOWNLOADS_DIR / ctx.guild.name / ctx.channel.name
        download_dir.mkdir(parents=True, exist_ok=True)
        count = 0
        async for msg in ctx.channel.history():
            if msg.attachments:
                logger.debug("attachment(s) found")
                for a in msg.attachments:
                    try:
                        await a.save(fp=download_dir / a.filename)
                    except Exception as e:  # noqa: BLE001 - TODO: Fix later
                        await ctx.send(f"Error downloading attachment from {msg.id}:\n```\n{e}\n```")
                    count += 1
        await ctx.send(f"Success: Downloaded {count} items.")
        return
