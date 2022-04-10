### Imports ###

import discord
from discord.ext import commands
from discord.utils import get

from typing import Optional 

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

    @commands.command(name="change_prefix", aliases=["cp"])
    @commands.has_permissions(administrator=True)
    async def change_prefix(self, ctx, new_prefix):
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
