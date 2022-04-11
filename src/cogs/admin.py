### Imports ###

import discord
from discord.ext import commands
from discord.utils import get

from typing import Optional, Literal

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
    async def set_bot_channel(ctx, channel):
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
    async def sync(self, ctx: commands.Context, guilds: Optional[Literal["all"]] = None):
        """Sync Compass's command tree"""
        gid = ctx.guild.id
        if not guilds:
            print(f"Syncing ships... Current guild: {gid}")
            fmt1 = await self.bot.tree.sync()
            fmt2 = await self.bot.tree.sync(guild=gid)
            await ctx.send(f"Bot tree synced: {fmt1} commands.\nSynced {len(fmt2)} commands to current guild.")
        elif guilds == "all":
            if gid != 393995277713014785:
                await ctx.send("You do not have permission to use that command in this server! (Glass Harbor only)")
                return
            fmt1 = await self.bot.tree.sync()      
            fmt2 = 0
            guilds = self.bot.db.get_all_guilds()
            for guild in guilds:
                await self.bot.tree.sync(guild=guild)
                fmt += 1
            await ctx.send(f"Bot tree synced: {fmt1} commands synced to {fmt2} of {len(guilds)} guilds.")
