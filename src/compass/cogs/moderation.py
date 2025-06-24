import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get
from loguru import logger

from compass.bot import CompassBot
from compass.config.bot_config import COLORS
from compass.utils.command_utils import move_message, send_embed
from compass.utils.utils import chunk_list, parse_args, dt_parse


async def mod_check_ctx(ctx: commands.Context):
    mod_roles = bot.db.get_mod_roles(ctx.guild.id)
    user_roles = [x.id for x in ctx.author.roles]
    if ctx.author.guild_permissions.administrator:
        return True
    if any(int(i) in user_roles for i in mod_roles):
        return True
    await ctx.send("You do not have permission to use this command.", delete_after=5.0)
    await asyncio.sleep(3)
    await ctx.message.delete()
    return False


async def mod_check_itx(itx: discord.Interaction):
    mod_roles = bot.db.get_mod_roles(itx.guild_id)
    user_roles = [x.id for x in itx.user.roles]
    if itx.user.guild_permissions.administrator:
        return True
    if any(int(i) in user_roles for i in mod_roles):
        return True
    await itx.response.send_message("You do not have permission to use this command.", ephemeral=True)
    return False


has_mod_ctx = commands.check(mod_check_ctx)
has_mod_itx = app_commands.check(mod_check_itx)


async def setup(bot):
    await bot.add_cog(Moderation(bot))


class Moderation(commands.Cog):
    def __init__(self, bot_: CompassBot):
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
        self,
        ctx: commands.Context,
        target: Union[discord.User, discord.TextChannel],
        *,
        embed_fields: str = "",
    ):
        target = target or ctx.channel
        args = parse_args(embed_fields)

        embed = discord.Embed(title=args.title, description=args.description, color=COLORS().random())

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
    @app_commands.command(name="purge", description="Deletes messages from current channel")
    async def _purge(
        self,
        itx: discord.Interaction,
        number: Optional[int] = None,
        before: str = "",
        after: str = "",
        reason: Optional[str] = None,
        # check: callable = None,
    ):
        # TODO: look into parsing before/after with https://github.com/scrapinghub/dateparser
        await itx.response.defer()
        await itx.channel.purge(limit=number, before=dt_parse(before), after=dt_parse(after), reason=reason)
        await itx.followup.send(f"{number} messages successfully purged!", ephemeral=True)

    @has_mod_itx
    @app_commands.command(name="moveto", description="Move a message to specified channel")
    async def _move_message(
        self, itx: discord.Interaction, channel: Union[discord.TextChannel, discord.Thread], message_id: str
    ):
        await move_message(itx, channel, message_id)

    @has_mod_itx
    @app_commands.command(name="giverole", description="Give a role to a user with optional duration")
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
                f'<@{target_user.id}> has been given the "{role.name}" role{" for " + str(dur) + " sec" if dur else ""}.'
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
    async def _take_role(self, itx: discord.Interaction, role: discord.Role, user: discord.Member, dur: Optional[int]):
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
                f'<@{bonked.id}> has had the "{role.name}" role removed{" for " + str(dur) + " sec" if dur else ""}.'
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
        if not required_roles:
            await itx.followup.send("No required roles set.")
            return
        role_mentions = [f"<@&{id}>" for id in required_roles]
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

        inactive_formatted = [
            f"{m[0]} - <t:{int(m[1].timestamp())}:f>" if m[1] else f"{m[0]} - No messages found " for m in inactive
        ]
        desc = "\n".join(inactive_formatted) if inactive_formatted else "No inactive members found."
        title = f"Inactive Members - {days} Days"
        if len(desc) < 4000:
            await itx.followup.send(embed=discord.Embed(title=title, description=desc, color=COLORS.random()))
        else:
            # split into multiple messages
            num_msgs = len(desc) // 4000 + 1
            chunked = list(chunk_list(inactive_formatted, len(inactive_formatted) // num_msgs))
            page = 1
            for sublist in chunked:
                await itx.followup.send(
                    embed=discord.Embed(
                        title=f"{title} (Page {page}/{num_msgs + 1})",
                        description="\n".join(sublist),
                        color=COLORS.random()
                    )
                )
                page += 1
        return
