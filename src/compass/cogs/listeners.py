import re
import time
import traceback
from datetime import datetime
from pathlib import Path

import discord
from discord.ext import commands
from discord.utils import get
from loguru import logger

from compass.bot import CompassBot
from compass.config.bot_config import COLORS, COMPASS_SRC, SERVERS, GuildData
from compass.utils.utils import download, getfilepath

cog_path = Path(__file__)


async def setup(bot):
    """Cog setup method"""
    await bot.add_cog(Listeners(bot))


class Listeners(commands.Cog):
    """Listeners for various events.

    Additional documentation can be found at:
    https://discordpy.readthedocs.io/en/stable/api.html?highlight=event#discord-api-events
    """

    def __init__(self, bot_: CompassBot):
        global bot
        bot = bot_

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """A global error handler cog."""
        message = ""
        if isinstance(error, commands.CommandNotFound):
            return  # We don't want to show an error for every command not found
        elif isinstance(error, commands.CommandOnCooldown):
            message = f"Please try again after {round(error.retry_after, 1)} seconds."
        elif isinstance(error, commands.MissingPermissions):
            message = "You are missing the required permissions to run this command!"
        elif isinstance(error, commands.MissingRequiredArgument):
            message = f"Missing a required argument: {error.param}"
        elif isinstance(error, commands.UserInputError):
            message = "Something about your input was wrong, please check your input and try again!"
        elif isinstance(error, commands.CheckFailure):
            pass
        else:
            tb = traceback.format_exception(error)
            err_msg = ""
            for i in tb:
                if "The above exception" in i:
                    break
                err_msg += i
            message = (
                f"Oh no! Something went wrong while running the command:\n`{ctx.message.content}`!\n```\n{err_msg}\n```"
            )
            # message += f"```\n{exception_type}\n{filename}\n{line_number}```"

        await ctx.send(embed=discord.Embed(description=message))

    @commands.Cog.listener("on_message")
    async def move_videos(self, msg: discord.Message):
        """Move videos to the specified video channel, if it is set."""
        if msg.author.bot:
            return
        vid_channel = bot.db.get_channel_vids(msg.guild.id)
        if vid_channel is None or msg.channel.id == vid_channel:
            return
        vid_links = ["youtube.com/watch?", "youtu.be/", "vimeo.com/", "dailymotion.com/video", "tiktok.com"]
        if not any(i in msg.content for i in vid_links) and not any("video" in a.content_type for a in msg.attachments):
            return
        else:
            files = []
            if msg.attachments:
                for a in filter(
                    lambda x,: x.size < msg.guild.filesize_limit,
                    msg.attachments,
                ):
                    await download(msg, a, "temp/moved_messages")
                    files.append(discord.File(getfilepath(msg, f"temp/moved_messages/{a.filename}")))
            newmessage = (
                f"{msg.author.mention} has uploaded a video.\n\n-# **__Original Message:__**\n>>> {msg.content}\n"
            )
            if any(a.size >= msg.guild.filesize_limit for a in msg.attachments):
                newmessage += "`Plus some files too large to resend`"
            # Move the message
            chan = await bot.fetch_channel(vid_channel)
            movedmessage = await chan.send(content=newmessage, files=files)
            # Delete original and notify author
            await msg.delete()
            await msg.channel.send(
                f"{msg.author.mention} - your message contained a video, and was moved to {movedmessage.jump_url}"
            )
            return

    @commands.Cog.listener("on_message")
    async def log_activity(self, message: discord.Message):
        """Log messages to the database."""
        if message.author.bot or isinstance(message.channel, discord.DMChannel):
            return
        track_activity = bot.db.get_field(message.guild.id, "track_activity")
        if not track_activity:
            return
        bot.db.add_or_update_user_log(
            message.guild.id, message.guild.name, message.author.id, message.author.name, message.created_at
        )

    @commands.Cog.listener("on_message")
    async def bat_react(self, message: discord.Message):
        """BATS ONLY: React with a bat emoji to messages with certain trigger words."""
        if (message.author.bot) or (message.guild.id not in [SERVERS.BATS, SERVERS.GLASS_TEST]):
            return
        triggers = [
            "bat",
            "bats",
            "batty",
            "batses",
            "<@&1375644186543390781>",  # @Announcements
            "<@&1210756079487688774>",  # @Example Role 2
        ]
        emoji = bot.get_emoji(1289965546900557997)  # <:bat_peek:1289965546900557997>
        if emoji is None and message.guild.id == SERVERS.BATS:
            logger.error("Bat emoji not found")
            emoji = str("🦇")

        # Extract role mentions first, then clean the rest
        role_mentions = re.findall(r"<@&\d+>", message.content)
        msg = re.sub(r"[^a-zA-Z\s]+", "", message.content)  # Clean to letters and spaces
        # Add back the role mentions
        msg = msg + " " + " ".join(role_mentions)

        if any(i.lower() in triggers for i in msg.split()):
            await message.add_reaction(emoji)
        # else:
        #     await message.add_reaction(str("❌"))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):  # reaction, user):
        """Flags and logs a message when a mod reacts to any message with the :mag: emoji"""

        message = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        reaction = payload.emoji
        emoji = "🔍"
        user = payload.member
        channel_id = bot.db.get_channel_logs(message.guild.id)
        log_channel = get(message.guild.text_channels, id=channel_id)
        if not log_channel:
            # await message.channel.send(
            #     f"Logs channel has not been set!\nUse `;set_logs_channel <#channel>` to set one."
            # )
            return
        if reaction.name == emoji:
            # Check for mod role
            mod_roles = bot.db.get_mod_roles(payload.guild_id)
            if mod_roles is None:
                return
            roles = [x.id for x in user.roles]
            if any(int(r) in roles for r in mod_roles):
                # Remove the reaction
                await message.remove_reaction("🔍", user)

                # Get info
                flagged_message, flagged_user = message, message.author
                dt = datetime.now()
                flagged_time = int(time.mktime(dt.timetuple()))

                # Create embed
                ce = discord.Embed(
                    title=f"Flagged Message", description=f"A message has been flagged in {flagged_message.channel}"
                )
                if flagged_message.content:
                    ce.add_field(name="Message content:", value=flagged_message.content, inline=False)
                ce.add_field(name="Flagged by:", value=user, inline=True)
                ce.add_field(name="Message Author:", value=flagged_user, inline=True)
                ce.add_field(
                    name="Message:",
                    value=f"[Jump to](https://discordapp.com/channels/{flagged_message.guild.id}/{flagged_message.channel.id}/{flagged_message.id})",
                    inline=True,
                )
                for i in flagged_message.attachments:
                    ce.add_field(name="Attachment:", value=f"{i.filename}")
                ce.add_field(name="Flagged at:", value=f"<t:{flagged_time}:R>")

                # Send embed to logs
                await log_channel.send(content=None, embed=ce)

        return

    #######################
    ### Guild Listeners ###
    #######################

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        # prep sending notif to Glass Harbor (for logging/debug)
        glass_guild = bot.get_guild(SERVERS.GLASS_HARBOR)
        chan_id = bot.db.get_channel_logs(glass_guild.id)
        channel = get(glass_guild.text_channels, id=chan_id)

        data = GuildData(guild).__dict__
        del data["guild"]

        if bot.db.add_guild(guild.id, data):
            await channel.send(embed=discord.Embed(description=f'Guild "{guild.name}" added to database.'))
        else:
            await channel.send(embed=discord.Embed(description=f'Guild "{guild.name}" already in database.'))
        return

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        # prep sending notif to Glass Harbor (for logging/debug)
        glass_guild = bot.get_guild(SERVERS.GLASS_HARBOR)
        chan_id = bot.db.get_channel_logs(glass_guild.id)
        channel = get(glass_guild.text_channels, id=chan_id)

        if bot.db.drop_guild_table(guild.id):
            await channel.send(embed=discord.Embed(description=f'Guild "{guild.name}" removed from database.'))
        else:
            await channel.send(embed=discord.Embed(description=f'Guild "{guild.name}" not found in database.'))
        return

    @commands.Cog.listener()
    async def on_guild_update(self, oldguild, newguild):
        bot.db.update_guild_name(oldguild.id, newguild.name)
        return

    ########################
    ### Member Listeners ###
    ########################

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        import io
        import httpx
        from PIL import Image

        guild = member.guild
        if guild.id != SERVERS.GLASS_HARBOR:
            return

        channel_id = bot.db.get_channel_welcome(guild_id=guild.id)
        if channel_id == 0:
            return
        channel = get(guild.text_channels, id=channel_id)

        av = httpx.get(member.display_avatar.url)
        ocean = Image.open(f"{COMPASS_SRC}/images/welcome_background.png")
        pfp = Image.open(io.BytesIO(av.content))
        pfp = pfp.resize((650, 650))
        ocean_w, ocean_h = ocean.size
        pfp_w, pfp_h = pfp.size
        offset = ((ocean_w - pfp_w) // 2, (ocean_h - pfp_h) // 2)
        base = Image.new("RGBA", ocean.size)
        base.paste(pfp, offset)
        img = Image.alpha_composite(base, ocean)

        with io.BytesIO() as image_binary:
            img.save(image_binary, "PNG")
            image_binary.seek(0)
            await channel.send(  # type: ignore
                content=f"Welcome, {member.mention}!",
                embed=discord.Embed(
                    title=f"Welcome to {guild.name}",
                    description=f"""
                    Please familiarize yourself with the Harbor <#954197139049816066>, 
                    have a look around, and enjoy your stay!

                    If you have any questions or concerns, feel free to mention the crew: 
                    <@&408812277836283908>, <@&428800694439641091>.
                    """,
                ),
                file=discord.File(fp=image_binary, filename="image.png"),
            )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        guild = member.guild
        if guild.id != SERVERS.GLASS_HARBOR:
            return
        channel_id = bot.db.get_channel_logs(guild_id=guild.id)
        if channel_id is None:
            return
        channel = get(guild.text_channels, id=channel_id)
        await channel.send(
            embed=discord.Embed(
                title=f"Goodbye, {member.name}!",
                description=f"{member.mention} has left the server.",
                color=COLORS.random(),
            )
        )
        bot.db.remove_user_log(guild.id, member.id)
