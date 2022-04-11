### Imports ###

import discord
from discord.ext import commands
from discord.utils import get

from typing import List, Optional, Literal, Union

from helper import * 

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
        print(f"Cog Online: {self.qualified_name}")

    @commands.command(name="set_prefix", aliases=["sp"])
    @commands.has_permissions(administrator=True)
    async def set_prefix(self, ctx, new_prefix):
        """
        Changes the bot's prefix for your server
        """
        self.bot.db.update_prefix(ctx.guild.id, new_prefix)
        await ctx.send("Prefix updated!")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def set_mod_roles(self, ctx, *, mod_roles: str):
        
        roles_list = mod_roles.split(" ")
        
        # Strip any <@&> from roles
        roles = []
        for role in roles_list:
            if role.startswith("<"):
                r = role[3:-1]
                roles.append(int(r))
            else:
                roles.append(int(role))   

        # Update mod roles in database
        self.bot.db.update_mod_roles(ctx.guild.id, roles)
        r = []
        for i in roles:
            r.append(f"<@&{i}>")
        await ctx.send(f"Mod roles set: {r}.")
        
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def set_logs_channel(self, ctx, channel): 
        # Get channel ID from mention
        nums = [i for i in channel if i.isdigit()]
        channel_id = int("".join(nums))
        chan = get(ctx.guild.text_channels, id=channel_id)
        if chan:
            self.bot.db.update_channel_logs(ctx.guild.id, channel_id)
            await ctx.send(f"Logs channel set to <#{channel_id}>")
            return True
        await ctx.send(f"{channel} is not a valid channel - please try again.")
        return False

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def set_bot_channel(self, ctx, channel):
        # Get channel ID from mention
        nums = [i for i in channel if i.isdigit()]
        channel_id = int("".join(nums))
        chan = get(ctx.guild.text_channels, id=channel_id)
        if chan:
            self.bot.db.update_channel_bot(ctx.guild.id, channel_id)
            await ctx.send(f"Bot channel set to <#{channel_id}>")
            return True
        await ctx.send(f"{channel} is not a valid channel - please try again.")
        return False    

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def sync(self, ctx: commands.Context, spec: Union[None, Literal["all"], Literal["guilds"]] = "all", *, guilds: Optional[str] = None):
        print("--------------------------------------\nSyncing ships...")
        if not spec:
            fmt = await self.bot.tree.sync()
            await self.bot.tree.sync(guild=ctx.guild.id)
            await ctx.send(f"Synced {len(fmt)} commands to guild.")
        if spec == "guilds":
            fmt1 = await self.bot.tree.sync()
            fmt2 = 0
            guilds = guilds.split(" ")
            for guild in guilds:
                print(f"Syncing to guild: {guild}")
                g = self.bot.get_guild(int(guild))
                print(f"Guild id: {g}")
                await self.bot.tree.sync(guild=g)
                fmt2 += 1
            await ctx.send(f"Bot tree synced: {len(fmt1)} commands synced to {fmt2} of {len(guilds)} guilds.")
        elif spec == "all":
            fmt1 = await self.bot.tree.sync()
            fmt2 = 0
            guilds = self.bot.db.get_all_guilds()
            for guild in guilds:
                print(f"Syncing to guild: {guild}")
                g = self.bot.get_guild(int(guild))
                print(f"Guild id: {g}")
                await self.bot.tree.sync(guild=g)
                fmt2 += 1
            await ctx.send(f"Bot tree synced: {len(fmt1)} commands to {fmt2} of {len(guilds)} guilds.")
        else:
            await ctx.send("Unexpected argument.\nExample usage: `;sync guilds 123456789987654321 987654321123456789`\nType `;help` for more info.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def synctree(self, ctx: commands.Context):#, spec: Optional[Literal["all"]] = None):
        """Sync the command tree to your guild"""
        fmt1 = await self.bot.tree.sync()
        fmt2 = await self.bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"Bot tree synced: {fmt1} commands.\nSynced {len(fmt2)} commands to current guild.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def syncall(self, ctx: commands.Context):
        """Sync the command tree to all guilds Compass is in"""
        # if ctx.guild.id != 393995277713014785:
        #     await ctx.send("You do not have permission to use that command in this server! (Glass Harbor only)")
        #     return
        fmt1 = await self.bot.tree.sync()      
        fmt2 = 0
        guilds = self.bot.db.get_all_guilds()
        for guild in guilds:
            await self.bot.tree.sync(guild=guild)
            fmt += 1
        await ctx.send(f"Bot tree synced: {fmt1} commands.\nSynced {len(fmt2)} commands to current guild")
