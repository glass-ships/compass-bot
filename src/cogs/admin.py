import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get

from typing import List, Optional, Literal, Union

# from utils.utils import * 
from utils.log_utils import get_logger
logger = get_logger(f"compass.{__name__}")

### Setup Cog

# Startup method
async def setup(bot):
    await bot.add_cog(Admin(bot))

# Define Class
class Admin(commands.Cog):
    def __init__(self, bot_):
        global bot
        bot = bot_

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")

    @commands.command(name="sync")
    @commands.has_permissions(administrator=True)
    async def _sync(self, ctx: commands.Context, spec: Union[Literal['dev'], Literal["guild"], None]):
        logger.info("Syncing ships...")
        if spec == 'dev':
            g = bot.get_guild(771161933301940224)
            await ctx.send(embed=discord.Embed(description=f"Copying command tree to {g}"), delete_after=5.0)
            bot.tree.copy_global_to(guild=g)
            fmt = await bot.tree.sync(guild=g)
            await ctx.send((f"Synced {len(fmt)} commands to dev guild."))
        elif spec == "guild":
            g = bot.get_guild(ctx.guild.id)
            fmt = await bot.tree.sync(guild=g)
            await ctx.send(embed=discord.Embed(description=f"Synced {len(fmt)} commands to guild."))
            logger.info("Ships synced!")
            return
        elif spec is None:
            fmt1 = await bot.tree.sync()
            await ctx.send(embed=discord.Embed(description=f"Synced bot tree ({len(fmt1)} commands)"))
            # fmt2 = 0
            #guilds = bot.db.get_all_guilds()
            #for guild in guilds:
            #    g = bot.get_guild(guild)
            #    await bot.tree.sync(guild=g)
            #    fmt2 += 1
            #await ctx.send(embed=discord.Embed(description=f"Bot tree synced: {len(fmt1)} commands to {len(guilds)} guilds."))
            #await ctx.send(f"Bot tree synced: {len(fmt1)} commands to {fmt2} of {len(guilds)} guilds.")
            logger.info("Ships synced!")
            return
        else:
            await ctx.send(embed=discord.Embed(description=f"Unexpected argument.\nType `;help` for more info."))
            logger.warning("Error syncing ships! (Bad argument)")
            return
    

    group_set = app_commands.Group(name="set",description="Group of commands to set bot settings")
    group_unset = app_commands.Group(name="unset",description="Group of commands to configure bot settings")
    
    @group_set.command(name="prefix")
    @commands.has_permissions(administrator=True)
    async def _prefix(self, itx: discord.Interaction, new_prefix: str):
        """
        Changes the bot's prefix for your server
        """
        bot.db.update_prefix(itx.guild_id, new_prefix)
        await itx.response.send_message(f"Prefix set to `{new_prefix}`")

    @group_set.command(name="mod_roles")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(mod_roles="List of mod roles (ID or mention)")
    async def _mod_roles(self, itx: discord.Interaction, mod_roles: str):
        roles_list = mod_roles.split(" ")
        roles = []
        for role in roles_list:
            if role.startswith("<"):
                roles.append(int(role[3:-1]))
            else:
                roles.append(int(role))
        bot.db.update_mod_roles(itx.guild_id, roles)
        await itx.response.send_message(f"Mod roles set: {mod_roles}")

    @group_set.command(name="member_role")
    @commands.has_permissions(administrator=True)
    async def _member_role(self, itx: discord.Interaction, role: discord.Role):
        bot.db.update_mem_role(itx.guild_id, role.id)
        await itx.response.send_message(f"Member role set: {role}")

    @group_set.command(name="dj_role")
    @commands.has_permissions(administrator=True)
    async def _dj_role(self, itx: discord.Interaction, role: discord.Role):
        bot.db.update_dj_role(itx.guild_id, role.id)
        await itx.response.send_message(f"DJ role set: {role}")

    @group_set.command(name="channel")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(option='What to specify a channel for', channel='Which channel to send to')
    @app_commands.autocomplete()
    async def _channel_set(self, itx: discord.Interaction, option: str, channel: discord.TextChannel):  
        if option == "logs":
            bot.db.update_channel_logs(itx.guild_id, channel.id)
        elif option == "bot":
            bot.db.update_channel_bot(itx.guild_id, channel.id)
        elif option == "videos":
            bot.db.update_channel_vids(itx.guild_id, channel.id)
        elif option == "music":
            bot.db.update_channel_music(itx.guild_id, channel.id)
        elif option == "lfg":
            bot.db.update_channel_lfg(itx.guild_id, channel.id)
        else:
            return False
        await itx.response.send_message(f"{option.title()} channel set to <#{channel.id}>.")
        return True

    @_channel_set.autocomplete('option')
    async def _channel_autocomplete(self, itx: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        options = ['logs', 'bot', 'music', 'videos', 'lfg']
        return [app_commands.Choice(name=option, value=option) for option in options if current.lower() in option.lower()]
    
    @group_unset.command(name="channel")
    @commands.has_permissions(administrator=True)
    @app_commands.autocomplete(option=_channel_autocomplete)
    async def _channel_unset(self, itx: discord.Interaction, option: str):  
        if option == "logs":
            bot.db.update_channel_logs(itx.guild_id, 0)
        elif option == "bot":
            bot.db.update_channel_bot(itx.guild_id, 0)
        elif option == "videos":
            bot.db.update_channel_vids(itx.guild_id, 0)
        elif option == "music":
            bot.db.update_channel_music(itx.guild_id, 0)
        elif option == "lfg":
            bot.db.update_channel_lfg(itx.guild_id, 0)
        else:
            await itx.response.send_message("Error: Unknown argument. Valid targets: logs, bot, music, videos")
            return False
        await itx.response.send_message(f"{option.title()} channel unset.")
        return True

    @group_unset.command(name="role")
    @commands.has_permissions(administrator=True)
    @app_commands.autocomplete()
    async def _role(self, itx: discord.Interaction, option: str):  
        if option == "mod":
            bot.db.update_mod_roles(itx.guild_id, [0])
        elif option == "member":
            bot.db.update_mem_role(itx.guild_id, 0)
        elif option == "dj":
            bot.db.update_dj_role(itx.guild_id, 0)
        else:
            await itx.response.send_message("Error: Unknown argument. Valid targets: mod, member, dj")
            return False
        await itx.response.send_message(f"{option.title()} role unset.")
        return True

    @_role.autocomplete('option')
    async def _roles_autocomplete(self, itx: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        options = ['mod', 'member', 'dj']
        return [app_commands.Choice(name=option, value=option) for option in options if current.lower() in option.lower()]

    #####

    @app_commands.command(name="allowvideos")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(channel="Which channel to allow/disallow videos in", switch="bool: True to allow videos")
    async def _allowvideos(self, itx: discord.Interaction, channel: discord.TextChannel, switch: bool):
        if switch == True:
            bot.db.add_videos_whitelist(itx.guild_id, channel.id)
            await itx.response.send_message(f"Videos allowed in <#{channel.id}>.")
        elif switch == False:
            bot.db.remove_videos_whitelist(itx.guild_id, channel.id)
            await itx.response.send_message(f"Videos not allowed in <#{channel.id}>.")


    #####
    
    @app_commands.command(name='reload')
    @commands.has_permissions(administrator=True)
    @app_commands.autocomplete()
    async def _reload(self, itx: discord.Interaction, module : str):
        """Reloads a module."""
        try:
            await bot.reload_extension(f"cogs.{module}")
        except Exception as e:
            await itx.response.send_message(f"\nError: \n```{e}```")
        else:
            await itx.response.send_message(f"\nModule: `{module}` reloaded.")

    @_reload.autocomplete('module')
    async def _reload_autocomplete(self, itx: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        options = ['admin', 'destiny', 'listeners', 'main', 'moderation', 'music', 'utils']
        return [app_commands.Choice(name=option, value=option) for option in options if current.lower() in option.lower()]

