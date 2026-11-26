import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from compass.bot import CompassBot
from compass.config.bot_config import COLORS

logger = logging.getLogger(__name__)

bot: CompassBot  # set in the cog's __init__ via `global bot`


async def setup(bot):
    """Cog setup method"""
    await bot.add_cog(Gaming(bot))


class LFGView(discord.ui.View):
    """Buttons on an LFG post.

    Persistent (no timeout, registered with `bot.add_view` in `Gaming.cog_load`): a post lives for an hour and must
    keep working across restarts. All state lives in the DB, keyed by the post's message ID, so one instance serves
    every post. Every callback must respond to the interaction, or Discord shows "This interaction failed".
    """

    def __init__(self):
        super().__init__(timeout=None)

    @staticmethod
    async def _reply(itx: discord.Interaction, content: str | None = None, **kwargs) -> None:
        await itx.response.send_message(content, ephemeral=True, **kwargs)

    @staticmethod
    async def _expired(itx: discord.Interaction) -> None:
        embed = discord.Embed(
            title="Inactive Post",
            description="This post is more than 60 minutes old and has expired.",
            color=COLORS.random(),
        )
        await LFGView._reply(itx, embed=embed)

    @discord.ui.button(label="View Roster", style=discord.ButtonStyle.primary, emoji="📖", custom_id="lfg_roster")
    async def view_roster(self, itx: discord.Interaction, button: discord.ui.Button):
        lfg = bot.db.get_lfg(lfg_id=itx.message.id)
        if lfg is None:
            await self._expired(itx)
            return
        leader = itx.guild.get_member(lfg["leader"])
        embed = discord.Embed(
            title=f"{leader.display_name if leader else 'Unknown'}'s LFG",
            color=COLORS().random(),
        )
        if leader:
            embed.set_thumbnail(url=leader.display_avatar.url)
        embed.add_field(name="Fireteam", value="\n".join(f"<@{i}>" for i in [lfg["leader"], *lfg["joined"]]))
        if lfg["standby"]:
            embed.add_field(name="Standby", value="\n".join(f"<@{i}>" for i in lfg["standby"]))
        await self._reply(itx, embed=embed)

    @discord.ui.button(
        label="Join", style=discord.ButtonStyle.success, emoji="<:_plus:1011101343030726687>", custom_id="lfg_join"
    )
    async def join_lfg(self, itx: discord.Interaction, button: discord.ui.Button):
        lfg = bot.db.get_lfg(lfg_id=itx.message.id)
        if lfg is None:
            await self._expired(itx)
            return
        if itx.user.id == lfg["leader"]:
            await self._reply(itx, "You cannot join your own LFG post.")
            return
        if itx.user.id in lfg["joined"] or itx.user.id in lfg["standby"]:
            await self._reply(itx, "You are already in the fireteam or on standby for this LFG post.")
            return
        if len(lfg["joined"]) + 1 == lfg["num_players"]:
            await itx.message.add_reaction("🇫")
        if not bot.db.update_lfg_join(lfg_id=itx.message.id, user_id=itx.user.id):
            await self._reply(itx, "Unable to join - the LFG may be full or you may already be in it.")
            return
        await self._reply(itx, "You've joined the fireteam.")
        embed = discord.Embed()
        embed.add_field(
            name=f"{itx.user.display_name} has joined your LFG",
            value="To view your roster, click the button below.",
        )
        await itx.channel.send(content=f"<@{lfg['leader']}>", embed=embed, delete_after=5.0)

    @discord.ui.button(
        label="Leave", style=discord.ButtonStyle.danger, emoji="<:_minus:1011101369245106176>", custom_id="lfg_leave"
    )
    async def leave_lfg(self, itx: discord.Interaction, button: discord.ui.Button):
        lfg = bot.db.get_lfg(lfg_id=itx.message.id)
        if lfg is None:
            await self._expired(itx)
            return
        if itx.user.id == lfg["leader"]:
            await self._reply(itx, "You cannot leave your own LFG post.")
            return
        if itx.user.id not in lfg["joined"] and itx.user.id not in lfg["standby"]:
            await self._reply(itx, "You are not in the fireteam or on standby for this LFG post.")
            return
        if not bot.db.update_lfg_leave(lfg_id=itx.message.id, user_id=itx.user.id):
            await self._reply(itx, "Unable to leave - you may not be in this LFG.")
            return
        await self._reply(itx, "You've left the fireteam.")
        embed = discord.Embed()
        embed.add_field(
            name=f"{itx.user.display_name} has left your LFG",
            value="To view your roster, click the button below.",
        )
        await itx.channel.send(content=f"<@{lfg['leader']}>", embed=embed, delete_after=5.0)


class Gaming(commands.Cog):
    def __init__(self, bot_: CompassBot):
        global bot
        bot = bot_

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")

    async def cog_load(self) -> None:
        # Re-attach the LFG buttons to existing posts (they're matched by custom_id), including after a restart
        bot.add_view(LFGView())

    @app_commands.command(name="lfg")
    @app_commands.describe(num_players="Number of players needed")
    async def _lfg(self, itx: discord.Interaction, num_players: int, activity: str, description: str = ""):
        await itx.response.send_message("Creating lfg...", ephemeral=True, delete_after=0.0)

        lfg_channel = bot.db.get_channel_lfg(itx.guild.id)
        if not lfg_channel or lfg_channel == 0 or itx.channel.id != lfg_channel:
            return
        else:
            lfg_channel = bot.get_channel(lfg_channel)

        embed = discord.Embed(
            title=f"LF{num_players}M: {activity}",
            color=COLORS().random(),
            description=description,
        )
        embed.set_footer(text=f"Fireteam Leader: {itx.user.name}", icon_url=itx.user.display_avatar.url)

        # Send the embed with the view attached
        view = LFGView()
        lfg_msg = await itx.channel.send(content="", embed=embed, view=view, delete_after=3600)
        lfg_id = lfg_msg.id

        bot.db.add_lfg(lfg_id=lfg_id, leader_id=itx.user.id, num_players=num_players)

        # Clean up after 1 hour
        await asyncio.sleep(3600)
        bot.db.drop_lfg(lfg_id)
