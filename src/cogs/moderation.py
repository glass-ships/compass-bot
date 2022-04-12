### Imports ###

import discord
from discord.ext import commands
from discord import app_commands
from discord.utils import get

from typing import Optional 

from helper import * 

### Setup Cog

# Startup method
async def setup(bot):
    await bot.add_cog(Moderation(bot))

# Define Class
class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Cog Online: {self.qualified_name}")

    @app_commands.command(name="purge")
    async def purge(self, itx: discord.Interaction, num: int = 0):
        """Purges x messages from current channel"""
        mod_roles = self.bot.db.get_mod_roles(itx.guild_id)
        if not await role_check_itx(itx, mod_roles):
            return
        await itx.channel.purge(limit=int(num))
        response = await itx.response.send_message(f"{num} messages successfully purged!", ephemeral=True)
        #await asyncio.sleep(2.0)
        #await response.delete()

    @app_commands.command(name="move")
    async def moveto(self, ctx, channel, msg_id):
        """
        Move a message to specified channel
        Example usage:
        ;moveto <#123456789987654321> 987654321123456789
        """

        await ctx.message.delete()

        # Get message to be moved
        msg = await ctx.fetch_message(msg_id)
        msg_content = msg.content
        msg_attachments = msg.attachments
        new_msg = msg_content
        if msg_attachments: 
            attachments = []
            for i in msg_attachments:
                attachments.append(i.url)
            new_msg += "\n\n" + "\n\n".join(attachments)

        # Get channel ID from mention
        nums = [i for i in channel if i.isdigit()]
        channel_id = int("".join(nums))
        chan = get(ctx.guild.text_channels, id=channel_id)

        # Send message to specified channel
        if chan:
            await chan.send(f"{msg.author.mention} - your message from <#{msg.channel.id}> has been moved to the appropriate channel:\n\n{new_msg}")
            await asyncio.sleep(1)
            await msg.delete()
            return True

        # Unless invalid channel
        await ctx.send(f"{channel} is not a valid channel - please try again.")
        return False

    @commands.command(name="temproleremove", aliases=["trr"])
    async def temproleremove(self, ctx, r, t: Optional[int]=30, user: discord.Member=None):
        """
        Remove specified role for x secs (30 default) from user, or self if none mentioned.
        Example usage:
        ;bonk 889212097706217493 60 @glass.ships#4517
        """
        
        # Check for mod
        mod_roles = self.bot.db.get_mod_roles(ctx.guild.id)
        if not await role_check(ctx, mod_roles):
            return

        await ctx.message.delete()
        
        role = get(ctx.guild.roles, id=int(r))    
        if not user:
            bonked = ctx.message.author
        else:
            bonked = user
        roles = [x.id for x in bonked.roles]
        if role.id in roles:
            await bonked.remove_roles(role)
            await ctx.send(f"<@{bonked.id}> has had the \"{role.name}\" role temporarily removed.", delete_after=6.0)
            await asyncio.sleep(t)
            await bonked.add_roles(role)
            await ctx.send(f"<@{bonked.id}> has had the \"{role.name}\" role added back.", delete_after=6.0)
        else:
            await ctx.send("Cannot remove role - user doesn't have it!",
                        delete_after=3.0)