from typing import List, Literal

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from compass.bot import CompassBot
from compass.config.bot_config import (
    CHANNEL_OPTIONS,
    COLORS,
    MODULES,
    ROLE_OPTIONS,
)
from compass.utils.utils import parse_args


async def setup(bot):
    """Cog setup method"""
    await bot.add_cog(Admin(bot))


class Admin(commands.Cog):
    def __init__(self, bot_: CompassBot):
        global bot
        bot = bot_

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")

    ########################################################################################################################
    ### Mostly debug commands, users shouldn't need these

    @commands.command(name="sync", description="Syncs the bot's command tree")
    @commands.has_permissions(administrator=True)
    async def _sync(self, ctx: commands.Context, *, sync_args: str = ""):
        """Sync the bot tree

        Args:
            clean: clear tree before syncing
            dev:   copy global commands to guild(s)
        """

        async def _update_msg(msg, new_content):
            await msg.edit(embed=discord.Embed(description=new_content, color=COLORS.random()))

        args = parse_args(sync_args)
        logger.debug(f"Syncing with args: {args} (from {sync_args})")
        guild = ctx.guild if args.guild is True else None

        desc = "Syncing bot tree..."
        msg = await ctx.send(embed=discord.Embed(description=desc, color=COLORS.random()))

        if args.clean is True:
            # This will remove all guild commands from the CommandTree and syncs,
            # which effectively removes all commands from the guild.
            logger.debug(f"\nClearing command tree from {guild.name if guild else 'all guilds'}...")
            desc += f"\nClearing command tree from {guild.name if guild else 'all guilds'}..."
            await _update_msg(msg, desc)
            bot.tree.clear_commands(guild=guild)

        if guild is not None:
            if args.dev:
                logger.debug(f"\nCopying global commands to guild: {guild.name}...")
                desc += f"\nCopying global commands to guild: {guild.name}..."
                await _update_msg(msg, desc)
                bot.tree.copy_global_to(guild=guild)

            synced = await bot.tree.sync(guild=guild)
            logger.debug(f"\nSynced {len(synced)} commands to guild.")
            desc += f"\nSynced {len(synced)} commands to guild."
            await _update_msg(msg, desc)
            return
        else:
            i = 1
            t = len(bot.guilds)
            for g in bot.guilds:
                if args.dev:
                    logger.debug(f"\nCopying global commands to guild: {g.name} ({i}/{t})...")
                    desc += f"\nCopying global commands to guild: {g.name} ({i}/{t})..."
                    await _update_msg(msg, desc)
                    bot.tree.copy_global_to(guild=g)
                synced = await bot.tree.sync(guild=g)
                logger.debug(f"\nSynced {len(synced)} commands to guild: {g.name} ({i}/{t}).")
                desc += f"\nSynced {len(synced)} commands to guild: {g.name} ({i}/{t})."
                await _update_msg(msg, desc)
                i += 1

        desc += "\nSync complete!"
        await _update_msg(msg, desc)
        return

    async def _sync_umbra(
        self, ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Literal["~", "*", "^"] | None = None
    ) -> None:
        if not guilds:
            if spec == "~":
                # This will sync all guild commands for the current context’s guild.
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                # This command copies all global commands to the current guild and syncs.
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                # This command will remove all guild commands from the CommandTree and syncs,
                # which effectively removes all commands from the guild.
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                # This takes all global commands within the CommandTree and sends them to Discord.
                synced = await ctx.bot.tree.sync()

            await ctx.send(f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}")
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

    @app_commands.command(name="reload", description="Force reloads a bot module")
    @commands.has_permissions(administrator=True)
    @app_commands.autocomplete()
    async def _reload(self, itx: discord.Interaction, module: str):
        """Reloads a module."""
        try:
            await bot.reload_extension(f"cogs.{module}")
        except Exception as e:
            await itx.response.send_message(f"\nError: \n```{e}```", ephemeral=True)
        else:
            await itx.response.send_message(f"\nModule: `{module}` reloaded.", ephemeral=True)

    @_reload.autocomplete("module")
    async def _reload_autocomplete(self, itx: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=option, value=option) for option in MODULES if current.lower() in option.lower()
        ]

    ########################################################################################################################

    group_set = app_commands.Group(name="set", description="Group of commands to set bot settings")
    group_unset = app_commands.Group(name="unset", description="Group of commands to configure bot settings")

    ####################
    ### Set Commands ###
    ####################

    @group_set.command(name="prefix", description="Set the bot's prefix for your server")
    @app_commands.checks.has_permissions(administrator=True)
    async def _prefix(self, itx: discord.Interaction, new_prefix: str):
        """
        Changes the bot's prefix for your server
        """
        bot.db.update_prefix(itx.guild_id, new_prefix)
        await itx.response.send_message(f"Prefix set to `{new_prefix}`")

    @group_set.command(name="track_activity", description="Set whether to keep track of user activity")
    @app_commands.checks.has_permissions(administrator=True)
    async def _track_activity(self, itx: discord.Interaction, track: bool):
        bot.db.add_or_update_field(itx.guild_id, "track_activity", track)
        await itx.response.send_message(f"Activity tracking set to `{track}`")

    @group_set.command(name="mod_roles", description="Set the mod roles for your server")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(mod_roles="List of mod roles (ID or mention)")
    async def _mod_roles(self, itx: discord.Interaction, mod_roles: str):
        roles_list = mod_roles.split(" ")
        roles = []
        for role in roles_list:
            if role.startswith("<"):
                roles.append(int(role[3:-1]))
            else:
                roles.append(int(role))
        bot.db.update_mod_roles(itx.guild_id, [str(role) for role in roles])
        await itx.response.send_message(f"Mod roles set: {mod_roles}")

    @group_set.command(name="member_role", description="Set the member role for your server")
    @app_commands.checks.has_permissions(administrator=True)
    async def _member_role(self, itx: discord.Interaction, role: discord.Role):
        bot.db.update_mem_role(itx.guild_id, role.id)
        await itx.response.send_message(f"Member role set: {role}")

    @group_set.command(name="required_roles", description="Set the required roles for your server")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(required_roles="List of required roles (ID or mention)")
    async def _required_roles(self, itx: discord.Interaction, required_roles: str):
        roles_list = required_roles.split(" ")
        roles = []
        for role in roles_list:
            if role.startswith("<"):
                roles.append(int(role[3:-1]))
            else:
                roles.append(int(role))
        bot.db.update_required_roles(itx.guild_id, [str(role) for role in roles])
        await itx.response.send_message(f"Required roles set: {required_roles}")

    ### Unset Commands ###

    @group_unset.command(name="role", description="Unset a role")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete()
    async def _role(self, itx: discord.Interaction, option: str):
        match option:
            case "mod":
                bot.db.update_mod_roles(itx.guild_id, None)
            case "member":
                bot.db.update_mem_role(itx.guild_id, None)
            case "required":
                bot.db.update_required_roles(itx.guild_id, None)
            case _:
                await itx.response.send_message("Error: Unknown argument. Valid targets: mod, member")
                return False
        await itx.response.send_message(f"{option.title()} role unset.")
        return True

    @_role.autocomplete("option")
    async def _roles_autocomplete(self, itx: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=option, value=option)
            for option in ROLE_OPTIONS
            if current.lower() in option.lower()
        ]

    ########################
    ### Channel Settings ###
    ########################

    @group_set.command(name="channel")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(option="What to specify a channel for", channel="Which channel to send to")
    @app_commands.autocomplete()
    async def _channel_set(self, itx: discord.Interaction, option: str, channel: discord.TextChannel):
        match option:
            case "bot":
                bot.db.update_channel_bot(itx.guild_id, channel.id)
            case "logs":
                bot.db.update_channel_logs(itx.guild_id, channel.id)
            case "welcome":
                bot.db.update_channel_welcome(itx.guild_id, channel.id)
            case "music":
                bot.db.update_channel_music(itx.guild_id, channel.id)
            case "lfg":
                bot.db.update_channel_lfg(itx.guild_id, channel.id)
            case "videos":
                bot.db.update_channel_vids(itx.guild_id, channel.id)
            # case "pins":
            #     bot.db.update_channel_pins(itx.guild_id, channel.id)
            case _:
                return False
        await itx.response.send_message(f"{option.title()} channel set to <#{channel.id}>.")
        return True

    @_channel_set.autocomplete("option")
    async def _channel_autocomplete(self, itx: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=option, value=option)
            for option in CHANNEL_OPTIONS
            if current.lower() in option.lower()
        ]

    @group_unset.command(name="channel")
    @commands.has_permissions(administrator=True)
    @app_commands.autocomplete(option=_channel_autocomplete)
    async def _channel_unset(self, itx: discord.Interaction, option: str):
        match option:
            case "bot":
                bot.db.update_channel_bot(itx.guild_id, None)
            case "logs":
                bot.db.update_channel_logs(itx.guild_id, None)
            case "welcome":
                bot.db.update_channel_welcome(itx.guild_id, None)
            case "music":
                bot.db.update_channel_music(itx.guild_id, None)
            case "lfg":
                bot.db.update_channel_lfg(itx.guild_id, None)
            case "videos":
                bot.db.update_channel_vids(itx.guild_id, None)
            # case "pins":
            #     bot.db.update_channel_pins(itx.guild_id, None)
            case _:
                await itx.response.send_message("Error: Unknown argument. Valid targets: logs, bot, music, videos")
                return False
        await itx.response.send_message(f"{option.title()} channel unset.")
        return True

    ######################
    ### Video Settings ###
    ######################

    @app_commands.command(name="allowvideos", description="Allow/disallow videos in a channel")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel="Which channel to allow/disallow videos in", allow="bool: True to allow videos")
    async def _allowvideos(self, itx: discord.Interaction, channel: discord.TextChannel, allow: bool):
        if allow is True:
            bot.db.add_videos_whitelist(itx.guild_id, channel.id)
            await itx.response.send_message(f"Videos allowed in <#{channel.id}>.")
        elif allow is False:
            bot.db.remove_videos_whitelist(itx.guild_id, channel.id)
            await itx.response.send_message(f"Videos not allowed in <#{channel.id}>.")
