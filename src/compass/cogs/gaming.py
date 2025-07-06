import asyncio
import re

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from compass.bot import CompassBot
from compass.config.bot_config import COLORS


async def setup(bot):
    """Cog setup method"""
    await bot.add_cog(Gaming(bot))


class lfgView(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="View Roster", style=discord.ButtonStyle.primary, emoji="📖", custom_id="lfg_roster")
    async def view_roster(self, itx: discord.Interaction, button: discord.ui.Button):
        await itx.response.defer()

        lfg = bot.db.get_lfg(lfg_id=itx.message.id)
        leader = bot.get_user(lfg["leader"])
        logger.debug(f"{lfg=}")
        if lfg is None:
            embed = discord.Embed(
                title="Inactive Post", description="This post is more than 60 minutes old and has expired."
            )
            await itx.channel.send(embed=embed, delete_after=10.0)
            return
        embed = discord.Embed(
            title=f"{leader.display_name}'s LFG",
            color=COLORS().random(),
        )
        embed.set_thumbnail(url=leader.avatar.url)
        fireteam = ""
        fireteam += f"<@{lfg['leader']}>\n"
        for i in lfg["joined"]:
            fireteam += f"<@{i}>\n"
        embed.add_field(name="Fireteam", value=fireteam)
        if len(lfg["standby"]) > 0:
            standby = ""
            for i in lfg["standby"]:
                standby += f"<@{i}>\n"
            embed.add_field(name="Standby", value=standby)
        await itx.channel.send(embed=embed, delete_after=10)

    @discord.ui.button(
        label="Join", style=discord.ButtonStyle.success, emoji="<:_plus:1011101343030726687>", custom_id="lfg_join"
    )
    async def join_lfg(self, itx: discord.Interaction, button: discord.ui.Button):
        lfg = bot.db.get_lfg(lfg_id=itx.message.id)
        if lfg is None:
            embed = discord.Embed(
                title="Inactive Post",
                description="This post is more than 60 minutes old and has expired.",
                color=COLORS.random(),
            )
            await itx.channel.send(embed=embed, delete_after=10.0)
            return
        if itx.user.id == lfg["leader"]:
            await itx.channel.send(f"{itx.user.mention} - you cannot join your own LFG post.", delete_after=5.0)
            return
        if str(itx.user.id) in lfg["joined"] or str(itx.user.id) in lfg["standby"]:
            await itx.channel.send(
                f"{itx.user.mention} You are already in the fireteam or on standby for this LFG post.",
                delete_after=5.0,
            )
            return
        if len(lfg["joined"]) + 1 == lfg["num_players"]:
            await itx.message.add_reaction("🇫")
        bot.db.update_lfg_join(lfg_id=itx.message.id, user_id=itx.user.id)
        embed = discord.Embed()
        embed.add_field(
            name=f"{itx.user.nick or itx.user.name} has joined your LFG",
            value=f"To view your roster, click the button below.",
        )
        await itx.channel.send(content=f"{itx.message.author.mention}", embed=embed, delete_after=5.0)

    @discord.ui.button(
        label="Leave", style=discord.ButtonStyle.danger, emoji="<:_minus:1011101369245106176>", custom_id="lfg_leave"
    )
    async def leave_lfg(self, itx: discord.Interaction, button: discord.ui.Button):
        lfg = bot.db.get_lfg(lfg_id=itx.message.id)
        if lfg is None:
            embed = discord.Embed(
                title="Inactive Post", description="This post is more than 60 minutes old and has expired."
            )
            await itx.channel.send(embed=embed, delete_after=10.0)
            return
        if itx.user.id == lfg["leader"]:
            await itx.channel.send(f"{itx.user.mention} - you cannot leave your own LFG post.", delete_after=5.0)
            return
        if str(itx.user.id) not in lfg["joined"] and str(itx.user.id) not in lfg["standby"]:
            await itx.channel.send(
                f"{itx.user.mention} You are not in the fireteam or on standby for this LFG post.",
                delete_after=5.0,
            )
            return
        bot.db.update_lfg_leave(lfg_id=itx.message.id, user_id=itx.user.id)
        embed = discord.Embed()
        embed.add_field(
            name=f"{itx.user.nick or itx.user.name} has left your LFG",
            value=f"To view your roster, click the button below.",
        )
        await itx.channel.send(content=f"{itx.message.author.mention}", embed=embed, delete_after=5.0)


class Gaming(commands.Cog):
    def __init__(self, bot_: CompassBot):
        global bot
        bot = bot_

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")

    @app_commands.command(name="lfg")
    @app_commands.describe(num_players="Number of players needed")
    async def _lfg(self, itx: discord.Interaction, num_players: int, activity: str, description: str = ""):
        await itx.response.send_message(f"Creating lfg...", ephemeral=True, delete_after=0.0)

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
        embed.set_footer(text=f"Fireteam Leader: {itx.user.name}", icon_url=itx.user.avatar.url)

        # Send the embed with the view attached
        view = lfgView()
        lfg_msg = await itx.channel.send(content="", embed=embed, view=view, delete_after=3600)
        lfg_id = lfg_msg.id

        bot.db.add_lfg(lfg_id=lfg_id, leader_id=itx.user.id, num_players=num_players)

        # Clean up after 1 hour
        await asyncio.sleep(3600)
        bot.db.drop_lfg(lfg_id)
