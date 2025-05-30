import asyncio
import re

import discord
from discord.ext import commands
from loguru import logger

from compass_bot.utils.bot_config import EMBED_COLOR


async def setup(bot):
    """Cog setup method"""
    await bot.add_cog(Gaming(bot))


class Gaming(commands.Cog):
    def __init__(self, bot_: commands.Bot):
        global bot
        bot = bot_

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")

    # LFM Create
    @commands.Cog.listener("on_message")
    async def create_lfg(self, message):
        if message.author.bot:
            return

        lfg_channel = bot.db.get_channel_lfg(message.guild.id)
        if lfg_channel == 0 or message.channel.id != lfg_channel:
            return

        msg = message.content
        lfm_format = r"[Ll][Ff]\d+[Mm]"
        search = re.search(lfm_format, msg)
        if search is None:
            return

        num_players = int(search.group()[2])
        bot.db.add_lfg(lfg_id=message.id, user_id=message.author.id, num_players=num_players)

        await message.add_reaction("<:_plus:1011101343030726687>")
        await message.add_reaction("<:_minus:1011101369245106176>")
        await message.add_reaction("📖")

        embed = discord.Embed(
            title="LFG session created!",
            color=EMBED_COLOR(),
            description="""
React with 📖 to see your active roster.
**Note:** Please do not edit your post, the bot will automatically react with 🇫 when session is full.
            """,
        )
        embed.set_footer(text=f"Fireteam Leader: {message.author.nick}", icon_url=message.author.avatar.url)
        await message.channel.send(embed=embed, delete_after=7.0)
        await asyncio.sleep(3600)
        bot.db.drop_lfg(message.guild.id, message.id)

    # LFM Update (Join/Leave/Check)
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member.bot:
            return

        guild = bot.get_guild(payload.guild_id)
        channel = bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        user = payload.member

        lfg_channel = bot.db.get_channel_lfg(guild.id)
        if lfg_channel == 0 or message.channel.id != lfg_channel:
            return

        emojis = {"join": "_plus", "leave": "_minus", "book": "📖", "full": "🇫"}

        lfg = bot.db.get_lfg(lfg_id=payload.message_id)

        if payload.emoji.name == emojis["join"]:
            await message.remove_reaction(payload.emoji, user)
            if lfg is None:
                embed = discord.Embed(
                    title="Inactive Post", description="This post is more than 60 minutes old and has expired."
                )
                await channel.send(embed=embed, delete_after=10.0)
                return
            if user.id == lfg["leader"]:
                return
            if str(user.id) in lfg["joined"] or str(user.id) in lfg["standby"]:
                await channel.send(
                    f"{user.mention} You are already in the fireteam or on standby for this LFG post.",
                    delete_after=10.0,
                )
                return
            if len(lfg["joined"]) + 1 == lfg["num_players"]:
                await message.add_reaction(emojis["full"])
            bot.db.update_lfg_join(lfg_id=payload.message_id, user_id=payload.user_id)
            embed = discord.Embed()
            embed.add_field(
                name=f"{user.nick or user.name} has joined your LFG",
                value=f"To view your roster, react to [your post]({message.jump_url}) with the {emojis['book']} emoji.",
            )
            await channel.send(content=f"{message.author.mention}", embed=embed, delete_after=10.0)
        elif payload.emoji.name == emojis["leave"]:
            await message.remove_reaction(payload.emoji, user)
            if lfg is None:
                embed = discord.Embed(
                    title="Inactive Post", description="This post is more than 60 minutes old and has expired."
                )
                await channel.send(embed=embed, delete_after=10.0)
                return
            if user.id == lfg["leader"]:
                return
            if len(lfg["joined"]) - 1 < lfg["num_players"]:
                await message.remove_reaction(emojis["full"], guild.get_member(bot.user.id))
            bot.db.update_lfg_leave(lfg_id=payload.message_id, user_id=payload.user_id)
            embed = discord.Embed()
            embed.add_field(
                name=f"{user.nick or user.name} has left your LFG",
                value=f"To view your roster, react to [your post]({message.jump_url}) with the {emojis['book']} emoji.",
            )
            await channel.send(content=f"{message.author.mention}", embed=embed, delete_after=10.0)
        elif payload.emoji.name == emojis["book"]:
            await message.remove_reaction(payload.emoji, user)
            if lfg is None:
                embed = discord.Embed(
                    title="Inactive Post", description="This post is more than 60 minutes old and has expired."
                )
                await channel.send(embed=embed, delete_after=10.0)
                return
            embed = discord.Embed(
                title=f"{message.author.name}'s LFG",
                color=EMBED_COLOR(),
            )
            embed.set_thumbnail(url=message.author.avatar.url)

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

            embed.set_footer(text=f"Requested by: {user.nick or user.name}")
            await bot.get_channel(payload.channel_id).send(embed=embed, delete_after=10.0)
