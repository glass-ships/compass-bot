import asyncio
import logging
from datetime import UTC, datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get

from compass.bot import CompassBot
from compass.components.pagination import Pagination
from compass.config.bot_config import COLORS
from compass.utils import dt_parse, parse_args
from compass.utils.checks import has_mod_ctx, has_mod_itx
from compass.utils.command_utils import move_message, send_embed

logger = logging.getLogger(__name__)


bot: CompassBot  # set in the cog's __init__ via `global bot`


async def setup(bot):
    await bot.add_cog(Moderation(bot))


########################################################################################################################
### Helpers


def can_manage_role(invoker: discord.Member, role: discord.Role) -> bool:
    """Check if the invoker can manage the given role."""
    if invoker.guild_permissions.administrator or invoker == invoker.guild.owner:
        return True
    return role < invoker.top_role


########################################################################################################################


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
        target: discord.User | discord.TextChannel,
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

        sent = await target.send(embed=embed)
        if isinstance(target, discord.TextChannel):
            await ctx.channel.send(f"Embed sent to {sent.jump_url}.", delete_after=5.0)
        elif isinstance(target, discord.User):
            await ctx.channel.send(f"Embed sent to {target.mention}.", delete_after=5.0)

        return

    @commands.command(name="lastmessage", description="Get the last message from a user")
    async def _last_message(self, ctx: commands.Context, user: discord.Member):
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
        mod_roles = bot.db.get_mod_roles(itx.guild_id) or []  # None when unset
        if not mod_roles:
            await itx.response.send_message("No mod roles set.", ephemeral=True)
            return
        r = ""
        for i in mod_roles:
            r += f"<@&{int(i)}>\n"
        await itx.response.send_message(embed=discord.Embed(description=f"Mod roles:\n{r}"))

    @has_mod_itx
    @app_commands.command(name="purge", description="Deletes messages from current channel")
    @app_commands.describe(
        number="How many messages to delete (1-1000)",
        before="Only delete messages before this time",
        after="Only delete messages after this time",
    )
    async def _purge(
        self,
        itx: discord.Interaction,
        number: app_commands.Range[int, 1, 1000],  # required: limit=None would delete the whole channel
        before: str = "",
        after: str = "",
        reason: str | None = None,
    ):
        await itx.response.defer(ephemeral=True)  # ephemeral: not in channel history, so the purge can't delete it
        before_dt = dt_parse(before) if before else None
        after_dt = dt_parse(after) if after else None
        if (before and before_dt is None) or (after and after_dt is None):
            await itx.followup.send(
                "Couldn't understand the `before`/`after` time; nothing was deleted.", ephemeral=True
            )
            return
        deleted = await itx.channel.purge(limit=number, before=before_dt, after=after_dt, reason=reason)
        await itx.followup.send(f"{len(deleted)} messages purged.", ephemeral=True)

    @has_mod_itx
    @app_commands.command(name="moveto", description="Move a message to specified channel")
    async def _move_message(
        self, itx: discord.Interaction, channel: discord.TextChannel | discord.Thread, message_id: str
    ):
        await move_message(itx, channel, message_id)

    @has_mod_itx
    @app_commands.command(name="giverole", description="Give a role to a user with optional duration")
    async def _give_role(self, itx: discord.Interaction, role: discord.Role, user: discord.Member, dur: int | None):
        await itx.response.defer()
        if not can_manage_role(itx.user, role):
            await itx.followup.send("You cannot give a role higher than your top role!", ephemeral=True)
            return
        role = get(itx.guild.roles, id=role.id)
        roles = [x.id for x in user.roles]
        if role.id not in roles:
            await user.add_roles(role)
            await itx.followup.send(
                f'<@{user.id}> has been given the "{role.name}" role{" for " + str(dur) + " sec" if dur else ""}.'
            )
            if dur:
                await asyncio.sleep(dur)
                await user.remove_roles(role)
                await itx.channel.send(f'<@{user.id}> has had the "{role.name}" role removed.')
        else:
            await itx.followup.send("Cannot give role - user already has it!")

    @has_mod_itx
    @app_commands.command(name="removerole", description="Remove role from a user with optional duration")
    @app_commands.rename(dur="duration")
    async def _take_role(self, itx: discord.Interaction, role: discord.Role, user: discord.Member, dur: int | None):
        await itx.response.defer()
        role = get(itx.guild.roles, id=role.id)
        if not can_manage_role(itx.user, role):
            await itx.followup.send("You cannot remove a role higher than your top role!", ephemeral=True)
            return
        roles = [x.id for x in user.roles]
        if role.id in roles:
            await user.remove_roles(role)
            await itx.followup.send(
                f'<@{user.id}> has had the "{role.name}" role removed{" for " + str(dur) + " sec" if dur else ""}.'
            )
            if dur:
                await asyncio.sleep(dur)
                await user.add_roles(role)
                # channel.send: the interaction token expires after 15 minutes, so a late followup would fail
                await itx.channel.send(f'<@{user.id}> has had the "{role.name}" role added back.')
        else:
            await itx.followup.send("Cannot remove role - user doesn't have it!")

    @has_mod_itx
    @app_commands.command(name="checkroles", description="Check for users missing required roles")
    async def _check_roles(self, itx: discord.Interaction):  # , roles: Optional[List[discord.Role]] = None):
        await itx.response.defer()
        required_roles = bot.db.get_required_roles(itx.guild_id)
        if not required_roles:
            await itx.followup.send("No required roles set.")
            return
        role_mentions = [f"<@&{_id}>" for _id in required_roles]
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
        if itx.guild is None:
            await itx.followup.send("This command can only be used in a server.")
            return
        await itx.followup.send("Checking for inactive members")
        inactive = []
        for member in itx.guild.members:
            if member.bot:
                continue
            last_message = bot.db.get_user_log(itx.guild.id, member.id)
            if not last_message or (last_message and datetime.now(UTC) - last_message > timedelta(days=days)):
                inactive.append((member.name, member.mention, last_message))

        def _get_page(page: int):
            emb = discord.Embed(
                title=f"Inactive Members - {days} days ({len(inactive)})",
                color=COLORS.random(),
            )
            offset = (page - 1) * per_page
            n = Pagination.compute_total_pages(len(inactive), per_page)
            for m in inactive[offset : offset + per_page]:
                emb.add_field(
                    name="",
                    value=f"{m[0]} ({m[1]}) - <t:{int(m[2].timestamp())}:f>"
                    if m[2]
                    else f"{m[0]} ({m[1]}) - No messages found",
                    inline=False,
                )
            emb.set_author(name=f"Requested by {itx.user}")
            emb.set_footer(text=f"Page {page} of {n}")
            return emb, n

        per_page = 10
        await Pagination(itx, _get_page).init()
