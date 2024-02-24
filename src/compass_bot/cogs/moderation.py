from datetime import datetime, timedelta, timezone
from typing import List, Optional, Union

import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get

from compass_bot.utils.utils import download, getfilepath, parse_args, send_embed
from compass_bot.utils.bot_config import EMBED_COLOR

from loguru import logger


async def mod_check_ctx(ctx):
    mod_roles = bot.db.get_mod_roles(ctx.guild.id)
    user_roles = [x.id for x in ctx.author.roles]
    if any(int(i) in user_roles for i in mod_roles):
        return True
    await ctx.send("You do not have permission to use this command.", delete_after=5.0)
    await asyncio.sleep(3)
    await ctx.message.delete()
    return False


async def mod_check_itx(itx: discord.Interaction):
    mod_roles = bot.db.get_mod_roles(itx.guild_id)
    user_roles = [x.id for x in itx.user.roles]
    if any(int(i) in user_roles for i in mod_roles):
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
    @commands.command(
        name="sendembed", aliases=["se"], description="Send an embed to a channel (fields not yet supported)"
    )
    async def _send_embed(
        self, ctx: commands.Context, target: Union[discord.User, discord.TextChannel], *, embed_fields: str = None
    ):
        target = target or ctx.channel
        args = parse_args(embed_fields)

        embed = discord.Embed(title=args.title, description=args.description, color=EMBED_COLOR())

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
    @app_commands.command(name="send", description="Send a message via the bot")
    async def _send(self, itx: discord.Interaction, channel: discord.TextChannel, message: str):
        await itx.response.defer(ephemeral=True)

        await channel.send(content=message)
        await itx.followup.send(f"Message sent to <#{channel.id}>.")

    @has_mod_itx
    @app_commands.command(name="dm", description="DM a user via the bot")
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
            r += f"<@&{int(i)}>\n"
        await itx.response.send_message(embed=discord.Embed(description=f"Mod roles:\n{r}"))

    @has_mod_itx
    @app_commands.command(name="purge", description="Deletes n messages from current channel")
    async def _purge(self, itx: discord.Interaction, number: int = 0):
        await itx.response.defer()
        await itx.channel.purge(limit=int(number))
        await itx.followup.send(f"{number} messages successfully purged!", ephemeral=True)

    @has_mod_itx
    @app_commands.command(name="moveto", description="Move a message to specified channel")
    async def _move_message(
        self, itx: discord.Interaction, channel: Union[discord.TextChannel, discord.Thread], message_id: str
    ):
        await itx.response.defer(ephemeral=True)
        # Get message to be moved
        msg = await itx.channel.fetch_message(int(message_id))
        newmsg = f"""
{msg.author.mention} - your message from <#{msg.channel.id}> has been moved to the appropriate channel.
─── **Original Message** ───

{msg.content}
"""
        # Get any attachments
        files = []
        if msg.attachments:
            for a in filter(lambda x: x.size <= itx.guild.filesize_limit, msg.attachments):
                await download(itx, a, "temp/moved_messages")
                files.append(discord.File(getfilepath(itx, f"temp/moved_messages/{a.filename}")))
        if any(a.size >= itx.guild.filesize_limit for a in msg.attachments):
            newmsg += (
                f"`File: {a.filename} too large to resend`"
                if len(msg.attachments) == 1
                else f"`Plus some files too large to resend`"
            )

        # Move the message
        await channel.send(content=newmsg, files=files)
        await msg.delete()
        await itx.followup.send(f"Message moved to <#{channel.id}>")

    @has_mod_itx
    @app_commands.command(name="give_role", description="Give a role to a user with optional duration")
    async def _give_role(self, itx: discord.Interaction, role: discord.Role, user: discord.Member, dur: Optional[int]):
        role = get(itx.guild.roles, id=role.id)
        if not user:
            target_user = itx.user
        else:
            target_user = user
        roles = [x.id for x in target_user.roles]
        if role.id not in roles:
            await target_user.add_roles(role)
            await itx.followup.send(
                f"<@{target_user.id}> has been given the \"{role.name}\" role{' for '+str(dur)+' sec' if dur else ''}."
            )
            if dur:
                await asyncio.sleep(dur)
                await target_user.remove_roles(role)
                await itx.channel.send(f'<@{target_user.id}> has had the "{role.name}" role removed.')
        else:
            await itx.followup.send("Cannot give role - user already has it!")

    @has_mod_itx
    @app_commands.command(name="removerole", description="Remove role from a user with optional duration")
    @app_commands.rename(dur="duration")
    async def _take_role(self, itx: discord.interactions, role: discord.Role, user: discord.Member, dur: Optional[int]):
        await itx.response.defer()
        role = get(itx.guild.roles, id=role.id)
        if not user:
            bonked = itx.user
        else:
            bonked = user
        roles = [x.id for x in bonked.roles]
        if role.id in roles:
            await bonked.remove_roles(role)
            await itx.followup.send(
                f"<@{bonked.id}> has had the \"{role.name}\" role removed{' for '+str(dur)+' sec' if dur else ''}."
            )
            if dur:
                await asyncio.sleep(dur)
                await bonked.add_roles(role)
                await itx.followup.send(f'<@{bonked.id}> has had the "{role.name}" role added back.')
        else:
            await itx.followup.send("Cannot remove role - user doesn't have it!")

    @has_mod_itx
    @app_commands.command(name="checkroles", description="Check for users missing required roles")
    async def _check_roles(self, itx: discord.Interaction):  # , roles: Optional[List[discord.Role]] = None):
        await itx.response.defer()
        required_roles = [id for id in bot.db.get_required_roles(itx.guild_id)]
        role_mentions = [f"<@&{id}>" for id in required_roles]
        if not required_roles:
            await itx.followup.send("No required roles set.")
            return
        response = await itx.followup.send(
            embed=discord.Embed(description=f"Checking for users without one of {' '.join(role_mentions)}")
        )
        missing = []
        for member in itx.guild.members:
            if member.bot:
                continue
            user_roles = [x.id for x in member.roles]
            if not any(int(i) in user_roles for i in required_roles):
                missing.append(member.mention)
        await response.edit(content=f"Found {len(missing)} members missing required roles.")
        missing = "\n".join(missing) if missing else "No members missing required roles."
        await send_embed(
            channel=itx.channel,
            title="Members Missing Required Roles",
            description=missing,
            image=None,
        )

    @commands.command(name="lastmessage", description="Get the last message from a user")
    async def _lastMessage(self, ctx: commands.Context, user: discord.Member):
        last_message = bot.db.get_user_log(ctx.guild.id, user.id)
        if last_message:
            await ctx.send(
                embed=discord.Embed(
                    description=f"{user.mention}'s last message on:\n<t:{int(last_message.timestamp())}:f>"
                )
            )
        else:
            await ctx.send(embed=discord.Embed(description=f"No messages found for {user.mention}"))

    @has_mod_itx
    @app_commands.command(name="checkinactive", description="Check for inactive users")
    async def _check_inactive(self, itx: discord.Interaction, days: int):
        await itx.response.defer()
        response = await itx.followup.send("Checking for inactive members...", wait=True)
        inactive = []
        for member in itx.guild.members:
            if member.bot:
                continue
            last_message = bot.db.get_user_log(itx.guild_id, member.id)
            if not last_message or (last_message and datetime.now(timezone.utc) - last_message > timedelta(days=days)):
                inactive.append((member.mention, last_message))
        await response.edit(content=f"Found {len(inactive)} inactive members.")
        inactive = "\n".join(
            [f"{m[0]} - <t:{int(m[1].timestamp())}:f>" if m[1] else f"{m[0]} - No messages found" for m in inactive]
        )
        await send_embed(
            channel=itx.channel,
            title="Inactive Members",
            description=inactive,
            image=None,
        )
        return
