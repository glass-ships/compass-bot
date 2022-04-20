### Imports ###

from xmlrpc.client import Boolean
import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get

from typing import List, Optional, Literal, Union

from helper import * 

logger = get_logger(__name__)

### Setup Cog

# Startup method
async def setup(bot):
    await bot.add_cog(Admin(bot))

# Define Class
class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")

    @commands.command(name="set_prefix", aliases=["sp"])
    @commands.has_permissions(administrator=True)
    async def setprefix(self, ctx, new_prefix):
        """
        Changes the bot's prefix for your server
        """
        self.bot.db.update_prefix(ctx.guild.id, new_prefix)
        await ctx.send("Prefix updated!")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def sync(self, ctx: commands.Context, spec: Union[Literal["all"], Literal["guild"]]):
        logger.info("Syncing ships...")
        if spec == "guild":
            fmt = await self.bot.tree.sync()
            g = self.bot.get_guild(ctx.guild.id)
            await self.bot.tree.sync(guild=g)
            self.bot.tree.copy_global_to(guild=g)
            await ctx.send(f"Synced {len(fmt)} commands to guild.")
            logger.info("Ships synced!")
            return
        elif spec == "all":
            fmt1 = await self.bot.tree.sync()
            fmt2 = 0
            guilds = self.bot.db.get_all_guilds()
            for guild in guilds:
                g = self.bot.get_guild(guild)
                await self.bot.tree.sync(guild=g)
                fmt2 += 1
            await ctx.send(f"Bot tree synced: {len(fmt1)} commands to {fmt2} of {len(guilds)} guilds.")
            logger.info("Ships synced!")
            return
        else:
            await ctx.send("Unexpected argument.\nExample usage: `;sync guilds 123456789987654321 987654321123456789`\nType `;help` for more info.")
            logger.warning("Error syncing ships! (Bad argument)")
            return
    
    group_set = app_commands.Group(name="set",description="Group of commands to set bot settings")
    group_unset = app_commands.Group(name="unset",description="Group of commands to configure bot settings")

    @group_set.command(name="channel")
    @commands.has_permissions(administrator=True)
    async def channel(self, itx: discord.Interaction, target: str, new_channel: discord.TextChannel):  
        if target == "logs":
            self.bot.db.update_channel_logs(itx.guild_id, new_channel.id)
        elif target == "bot":
            self.bot.db.update_channel_bot(itx.guild_id, new_channel.id)
        elif target == "videos":
            self.bot.db.update_channel_vids(itx.guild_id, new_channel.id)
        else:
            await itx.response.send_message("Error: Unknown argument. Valid targets: logs, bot, videos")
            return False
        await itx.response.send_message(f"{target.title()} channels set to <#{new_channel.id}>.")
        return True

    @group_set.command(name="modroles")
    @commands.has_permissions(administrator=True)
    async def modroles(self, itx: discord.Interaction, mod_roles: str):
        roles_list = mod_roles.split(" ")
        roles = []
        for role in roles_list:
            if role.startswith("<"):
                r = role[3:-1]
                roles.append(int(r))
            else:
                roles.append(int(role))
        self.bot.db.update_mod_roles(itx.guild_id, roles)
        await itx.response.send_message(f"Mod roles set: {mod_roles}", ephemeral=True)

    @group_set.command(name="allowvideos")
    @commands.has_permissions(administrator=True)
    async def allowvideos(self, itx: discord.Interaction, channel: discord.TextChannel, switch: Boolean):
        if switch == True:
            self.bot.db.add_videos_whitelist(itx.guild_id, channel.id)
            await itx.response.send_message(f"Videos allowed in <#{channel.id}>.")
        elif switch == False:
            self.bot.db.remove_videos_whitelist(itx.guild_id, channel.id)
            await itx.response.send_message(f"Videos not allowed in <#{channel.id}>.")

    @group_unset.command(name="channel")
    @commands.has_permissions(administrator=True)
    async def channel(self, itx: discord.Interaction, target: str):  
        if target == "logs":
            self.bot.db.update_channel_logs(itx.guild_id, 0)
        elif target == "bot":
            self.bot.db.update_channel_bot(itx.guild_id, 0)
        elif target == "videos":
            self.bot.db.update_channel_vids(itx.guild_id, 0)
        else:
            await itx.response.send_message("Error: Unknown argument. Valid targets: logs, bot, videos")
            return False
        await itx.response.send_message(f"{target.title()} channels unset.")
        return True

def old_set_commands():     
    # @commands.command()
    # @commands.has_permissions(administrator=True)
    # async def setmodroles(self, ctx, *, mod_roles: str):  
    #     roles_list = mod_roles.split(" ")
    #     # Strip any <@&> from roles
    #     roles = []
    #     for role in roles_list:
    #         if role.startswith("<"):
    #             r = role[3:-1]
    #             roles.append(int(r))
    #         else:
    #             roles.append(int(role))   

    #     # Update mod roles in database
    #     self.bot.db.update_mod_roles(ctx.guild.id, roles)
    #     await ctx.send(f"Mod roles set: {mod_roles}")

    # @commands.command()
    # @commands.has_permissions(administrator=True)
    # async def setlogschannel(self, ctx, channel): 
    #     # Get channel ID from mention
    #     nums = [i for i in channel if i.isdigit()]
    #     channel_id = int("".join(nums))
    #     chan = get(ctx.guild.text_channels, id=channel_id)
    #     if chan:
    #         self.bot.db.update_channel_logs(ctx.guild.id, channel_id)
    #         await ctx.send(f"Logs channel set to <#{channel_id}>")
    #         return True
    #     await ctx.send(f"{channel} is not a valid channel - please try again.")
    #     return False

    # @commands.command()
    # @commands.has_permissions(administrator=True)
    # async def setbotchannel(self, ctx, channel):
    #     # Get channel ID from mention
    #     nums = [i for i in channel if i.isdigit()]
    #     channel_id = int("".join(nums))
    #     chan = get(ctx.guild.text_channels, id=channel_id)
    #     if chan:
    #         self.bot.db.update_channel_bot(ctx.guild.id, channel_id)
    #         await ctx.send(f"Bot channel set to <#{channel_id}>")
    #         return True
    #     await ctx.send(f"{channel} is not a valid channel - please try again.")
    #     return False
    pass
