### Imports ###
import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get

from datetime import datetime
import shlex
from typing import Optional, Union

from utils.helper import * 

logger = get_logger(__name__)

### Setup Cog

# Startup method
async def setup(bot):
    await bot.add_cog(Moderation(bot))

# Define Class
class Moderation(commands.Cog):
    def __init__(self, bot_):
        global bot
        bot = bot_

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")

    ##### Chat Commands #####

    @commands.command(name='send', aliases=['say'], description="Send a message via the bot")
    async def _send(self, ctx: commands.Context, message: str=None, channel: discord.TextChannel=None):
        if channel is None:
            channel = ctx.channel
        if message is None:
            await ctx.channel.send("Please enter a message to be sent.")
            return
        await channel.send(content=message)
        await ctx.message.delete()
        await ctx.channel.send(f"Message sent to <#{channel.id}>.", delete_after=5.0)

    @commands.command(name='sendembed', aliases=['se'], description="Send an embed to a channel (fields not yet supported)")
    async def _send_embed(self,
        ctx: commands.Context, channel: discord.TextChannel, *, embed_fields: str = None):
        if channel is None:
            channel = ctx.channel
        
        args = shlex.split(embed_fields)
        post_options = ['image', 'thumbnail', 'footer']
        opts = {}
        post_opts = {}
        for i in range(len(args)):
            arg = args[i]
            if arg.startswith('--'):
                if arg.strip('-') not in post_options:
                    opts[arg.strip('-')] = args[i+1]
                else:
                    post_opts[arg.strip('-')] = args[i+1]
        print(opts)
        print(post_opts)

        embed = discord.Embed().from_dict(opts)

        if 'footer' in post_opts.keys():
            embed.set_footer(icon_url=post_opts['footer'])
        if 'image' in post_opts.keys():
            embed.set_image(url=post_opts['image'])
        if 'thumbnail' in post_opts.keys():
            embed.set_thumbnail(url=post_opts['thumbnail'])
        
        await channel.send(embed=embed)
        await ctx.channel.send(f"Embed sent to <#{channel.id}>.", delete_after=5.0)


    @commands.command(name="get_mod_roles", description="Get a list of guild's mod roles", aliases=['modroles'])
    async def _get_mod_roles(self, ctx):
        mod_roles = bot.db.get_mod_roles(ctx.guild.id)
        r = []
        for i in mod_roles:
            r.append(f"<@&{i}>")
        await ctx.send(embed=discord.Embed(description=f"Mod roles: {r}."))

    ##### Slash Commands ######

    @app_commands.command(name="purge", description="Deletes n messages from current channel")
    async def _purge(self, itx: discord.Interaction, number: int = 0):
        mod_roles = bot.db.get_mod_roles(itx.guild_id)
        if not await role_check_itx(itx, mod_roles):
            return
        await itx.response.defer()
        await itx.channel.purge(limit=int(number))
        await itx.followup.send(f"{number} messages successfully purged!", ephemeral=True)

    @app_commands.command(name="moveto", description="Move a message to specified channel")
    async def _move_message(self, itx: discord.Interaction, channel: Union[discord.TextChannel, discord.Thread], message_id: str):
        
        # Check for mod
        mod_roles = bot.db.get_mod_roles(itx.guild_id)
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
                    discord.File(getfilepath(itx, f"temp/moved_messages/{a.filename}"))
                )
        if any(a.size >= itx.guild.filesize_limit for a in msg.attachments):
            newmsg += f"`File: {a.filename} too large to resend`" if len(msg.attachments) == 1 else f"`Plus some files too large to resend`"

        # Move the message
        await channel.send(content=newmsg, files=files)
        await msg.delete()
        await itx.followup.send(f"Message moved to <#{channel.id}>")
    
    async def _add_role():
        pass

    @app_commands.command(name="removerole", description="Remove role from a user with optional duration")
    @app_commands.rename(dur="duration")#, role="Role", user="User")
    async def _role_remove(self, itx: discord.interactions, role: discord.Role, user: discord.Member, dur: Optional[int]):

        # Check for mod
        assert await role_check_itx(itx, bot.db.get_mod_roles(itx.guild_id))

        await itx.response.defer()

        role = get(itx.guild.roles, id=role.id)    
        if not user:
            bonked = itx.user
        else:
            bonked = user
        roles = [x.id for x in bonked.roles]
        if role.id in roles:
            await bonked.remove_roles(role)
            await itx.followup.send(f"<@{bonked.id}> has had the \"{role.name}\" role removed{' for '+str(dur)+' sec' if dur else ''}.")
            if dur:
                await asyncio.sleep(dur)
                await bonked.add_roles(role)
                await itx.followup.send(f"<@{bonked.id}> has had the \"{role.name}\" role added back.")
        else:
            await itx.followup.send("Cannot remove role - user doesn't have it!")

    @commands.command(name="checkinactive", aliases=['ci'])
    async def _check_user_activity(self, ctx):
        """Checks server activity for members in the last 14 days"""
        
        # Check for mod
        logger.info("Checking for mod role...")
        mod_roles = bot.db.get_mod_roles(ctx.guild.id)
        if not await role_check(ctx, mod_roles):
            return
        
        today = datetime.now()
        inactive_users = []

        logger.info("Checking for inactive users...")

        member_role_id = bot.db.get_mem_role(ctx.guild.id)
        member_role = ctx.guild.get_role(member_role_id)
        for user in member_role.members:
            pass

    