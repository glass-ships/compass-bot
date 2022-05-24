### Imports ###

from datetime import datetime
from re import T
import discord
from discord.ext import commands
from discord import app_commands
from discord.utils import get

from typing import Optional, Union

from helper import * 

logger = get_logger(__name__)

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
        logger.info(f"Cog Online: {self.qualified_name}")

    @app_commands.command(name="purge", description="Deletes n messages from current channel")
    async def purge(self, itx: discord.Interaction, number: int = 0):
        mod_roles = self.bot.db.get_mod_roles(itx.guild_id)
        if not await role_check_itx(itx, mod_roles):
            return
        await itx.channel.purge(limit=int(number))
        await itx.response.send_message(f"{number} messages successfully purged!", ephemeral=True)

    @app_commands.command(name="moveto", description="Move a message to specified channel")
    async def moveto(self, itx: discord.Interaction, channel: Union[discord.TextChannel, discord.Thread], message_id: str):
        
        # Check for mod
        mod_roles = self.bot.db.get_mod_roles(itx.guild_id)
        if not await role_check_itx(itx, mod_roles):
            return

        await itx.response.defer(ephemeral=True)

        # Get message to be moved
        msg = await itx.channel.fetch_message(int(message_id))
        newmsg = f"{msg.author.mention} - your message from <#{msg.channel.id}> has been moved to the appropriate channel.\n─── **Original Message** ───\n\n {msg.content}\n"

        # Get any attachments
        files = []
        if msg.attachments:            
            for a in filter(lambda x: x.size <= itx.guild.filesize_limit, msg.attachments):
                await download(itx, a, 'temp/moved_messages')
                files.append(
                    discord.File(getfile(itx, f"temp/moved_messages/{a.filename}"))
                )
        if any(a.size >= itx.guild.filesize_limit for a in msg.attachments):
            newmsg += f"`Plus some files too large to resend`"

        # Move the message
        await channel.send(
           content = newmsg,
           files = files
        )
        await msg.delete()
        await itx.followup.send(f"Message moved to <#{channel.id}>")

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

    @commands.command(name="activitycheck")
    async def activitycheck(self, ctx):
        """Checks server activity for members in the last 14 days"""
        
        # Check for mod
        logger.info("Checking for mod role...")
        mod_roles = self.bot.db.get_mod_roles(ctx.guild.id)
        if not await role_check(ctx, mod_roles):
            return
        
        today = datetime.now()
        inactive_users = []

        logger.info("Checking for inactive users...")

        member_role_id = self.bot.db.get_mem_role(ctx.guild.id)
        member_role = ctx.guild.get_role(member_role_id)
        for user in member_role.members:
            active = True

            logger.info("Fetching last message...")

            last_message = [m async for m in user.history()]
            print(last_message)
            return
            duration = today - last_message[0].created_at
            if duration.days >= 14:
                active = False

            # voice_activity = "prob need a database to track this"
            # if voice_activity < "5 minutes in last 14 days": 
            #     active = False
            
            if active == False:
                inactive_users.append(user.id)
            
            # Send embed to logs
            channel_id = self.bot.db.get_channel_logs(ctx.guild.id)
            channel = get(ctx.guild.text_channels, id=channel_id)
            if channel:
                await channel.send(
                    content=f"The following users have been inactive in Discord for at least 14 days:\n{inactive_users}"
                )
            else:
                await ctx.send(f"Logs channel has not been set!\nUse `;set_logs_channel <#channel>` to set one.")
