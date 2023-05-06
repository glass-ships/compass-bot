from typing import Optional, Union

import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get
import shlex

from compass_bot.utils.utils import download, getfilepath, parse_args
from compass_bot.utils.bot_config import EMBED_COLOR

from loguru import logger


async def mod_check_ctx(ctx):
    mod_roles = bot.db.get_mod_roles(ctx.guild.id)
    user_roles = [x.id for x in ctx.author.roles]
    if any(i in user_roles for i in mod_roles):
        return True
    await ctx.send("You do not have permission to use this command.", delete_after=5.0)
    await asyncio.sleep(3)
    await ctx.message.delete()
    return False

async def mod_check_itx(itx: discord.Interaction):
    mod_roles = bot.db.get_mod_roles(itx.guild_id)
    user_roles = [x.id for x in itx.user.roles]
    if any(i in user_roles for i in mod_roles):
        return True
    await itx.response.send_message("You do not have permission to use this command.", ephemeral=True)
    return False

has_mod_ctx = commands.check(mod_check_ctx)
has_mod_itx = app_commands.check(mod_check_itx)


async def setup(bot):
    await bot.add_cog(Moderation(bot))


class Moderation(commands.Cog):
    def __init__(self, bot_):
        global bot
        bot = bot_

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")

    ##################### 
    ### Chat Commands ###
    #####################
    
    @has_mod_ctx
    @commands.command(name='sendembed', aliases=['se'], description="Send an embed to a channel (fields not yet supported)")
    async def _send_embed(self, ctx: commands.Context, target: Union[discord.User, discord.TextChannel], *, embed_fields: str = None):
        target = target or ctx.channel
        args = parse_args(embed_fields)

        embed = discord.Embed(title = args.title, description = args.description, color = EMBED_COLOR())

        if args.image:
            embed.set_image(url=args.image)
        if args.thumbnail:
            embed.set_thumbnail(url=args.thumbnail)
        if args.footer or args.footer_image:
            embed.set_footer(text=args.footer, icon_url=args.footer_image)
        
        await target.send(embed=embed)
        if isinstance(target, discord.TextChannel):
            await ctx.channel.send(f"Embed sent to <#{target.id}>.", delete_after=5.0)
        elif isinstance(target, discord.User):
            await ctx.channel.send(f"Embed sent to {target.mention}.", delete_after=5.0)

        return


    ######################
    ### Slash Commands ###
    ######################
    
    @has_mod_itx
    @app_commands.command(name='send', description="Send a message via the bot")
    async def _send(self, itx: discord.Interaction, channel: discord.TextChannel, message: str):
        await itx.response.defer(ephemeral=True)
        
        await channel.send(content=message)
        await itx.followup.send(f"Message sent to <#{channel.id}>.")

    @has_mod_itx
    @app_commands.command(name='dm', description="DM a user via the bot")
    async def _send_dm(self, itx: discord.Interaction, user: discord.User, message: str):
        await itx.response.defer(ephemeral=True)
        await user.send(content=message)
        await itx.followup.send(f"Message sent to {user.mention}.")
    
    @has_mod_itx
    @app_commands.command(name="getmodroles", description="Get a list of guild's mod roles")
    async def _get_mod_roles(self, itx: discord.Interaction):
        mod_roles = bot.db.get_mod_roles(itx.guild_id)
        r = ""
        for i in mod_roles:
            r += f"<@&{i}>\n"
        await itx.response.send_message(embed=discord.Embed(description=f"Mod roles:\n{r}"))

    
    @has_mod_itx
    @app_commands.command(name="purge", description="Deletes n messages from current channel")
    async def _purge(self, itx: discord.Interaction, number: int = 0):
        await itx.response.defer()
        await itx.channel.purge(limit=int(number))
        await itx.followup.send(f"{number} messages successfully purged!", ephemeral=True)

    
    @has_mod_itx
    @app_commands.command(name="moveto", description="Move a message to specified channel")
    async def _move_message(self, itx: discord.Interaction, channel: Union[discord.TextChannel, discord.Thread], message_id: str):
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

      
    async def _give_role():
        pass

    @has_mod_itx
    @app_commands.command(name="removerole", description="Remove role from a user with optional duration")
    @app_commands.rename(dur="duration")
    async def _remove_role(self, itx: discord.interactions, role: discord.Role, user: discord.Member, dur: Optional[int]):
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

