import time, traceback
from datetime import datetime
from pathlib import Path

import discord
from discord.ext import commands
from discord.utils import get

from utils.bot_config import GLASS_HARBOR, GuildData
from utils.utils import download, getfilepath
from utils.log_utils import get_logger

logger = get_logger(f"compass.{__name__}")
cog_path = Path(__file__)


async def setup(bot):
    """Cog setup method"""
    await bot.add_cog(Listeners(bot))


class Listeners(commands.Cog):
    def __init__(self, bot_):
        global bot 
        bot = bot_

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")


    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """A global error handler cog."""
        message = ''
        if isinstance(error, commands.CommandNotFound):
            return  # Return because we don't want to show an error for every command not found
        elif isinstance(error, commands.CommandOnCooldown):
            message = f"This command is on cooldown. Please try again after {round(error.retry_after, 1)} seconds."
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
            err_msg = ''
            for i in tb:
                if 'The above exception' in i:
                    break
                err_msg += i
            message = f"Oh no! Something went wrong while running the command!\n```\n{err_msg}\n```"#```\n{exception_type}\n{filename}\n{line_number}```"

        await ctx.send(embed=discord.Embed(description=message))#, delete_after=60)
        await ctx.message.delete(delay=5)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Move videos"""

        if message.author.bot:
            return

        vid_channel = bot.db.get_channel_vids(message.guild.id)
        if vid_channel == 0 or message.channel.id != vid_channel:
            return

        vid_links = ["youtube.com/watch?","youtu.be/","vimeo.com/","dailymotion.com/video","tiktok.com"]
        newmessage = f"{message.author.name} has uploaded a video.\n─── **Original Message** ───\n\n{message.content}\n"
        
        if any(i in message.content for i in vid_links):
            files = []
            if message.attachments:            
                for a in filter(lambda x: x.size < message.guild.filesize_limit, message.attachments):
                    await download(message, a, 'temp/moved_messages')
                    files.append(
                        discord.File(getfilepath(message, f"temp/moved_messages/{a.filename}"))
                    )
            if any(a.size >= message.guild.filesize_limit for a in message.attachments):
                newmessage += "`Plus some files too large to resend`"

            # Move the message
            chan = await bot.fetch_channel(vid_channel)
            movedmessage = await chan.send(
                content = newmessage,
                files = files
            )

            # Delete original and notify author
            await message.delete()
            await message.channel.send(f"{message.author.mention} - your message contained a video, and was moved to <#{vid_channel}>.\n**Link:** \nhttps://discord.com/channels/{message.guild.id}/{vid_channel}/{movedmessage.id}")

            return
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):# reaction, user):
        """
        When a mod reacts to any message with the :mag: emoji,
        Bot will flag the message and send the info to a logs channel
        """
        message = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        reaction = payload.emoji
        emoji = '🔍'
        user = payload.member
        
        if reaction.name == emoji:  
            # Check for mod role      
            
            mod_roles = bot.db.get_mod_roles(payload.guild_id)
            roles = [x.id for x in user.roles]
            if any(r in roles for r in mod_roles):

                # Remove the reaction           
                await message.remove_reaction('🔍', user)

                # Get info
                flagged_message, flagged_user = message, message.author
                dt = datetime.now()
                flagged_time = int(time.mktime(dt.timetuple()))

                # Create embed
                ce = discord.Embed(
                    title=f"Flagged Message",
                    description=f"A message has been flagged in {flagged_message.channel}"
                )
                if flagged_message.content:
                    ce.add_field(name="Message content:",
                            value=flagged_message.content,
                            inline=False
                    )           
                ce.add_field(name="Flagged by:", value=user, inline=True)
                ce.add_field(name="Message Author:", value=flagged_user, inline=True)
                ce.add_field(name="Message:", value=f"[Jump to](https://discordapp.com/channels/{flagged_message.guild.id}/{flagged_message.channel.id}/{flagged_message.id})", inline=True)
                for i in flagged_message.attachments:
                    ce.add_field(name="Attachment:", value=f"{i.filename}")
                ce.add_field(name="Flagged at:", value=f"<t:{flagged_time}:R>")

                # Send embed to logs
                channel_id = bot.db.get_channel_logs(flagged_message.guild.id)
                channel = get(flagged_message.guild.text_channels, id=channel_id)
                if channel:
                    await channel.send(content=None, embed=ce)
                else:
                    await flagged_message.channel.send(f"Logs channel has not been set!\nUse `;set_logs_channel <#channel>` to set one.")
        return

    #######################              
    ### Guild Listeners ###
    #######################
                    
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        # prep sending notif to Glass Harbor (for logging/debug)
        glass_guild = bot.get_guild(GLASS_HARBOR)
        chan_id = bot.db.get_channel_logs(glass_guild.id)
        channel = get(glass_guild.text_channels, id=chan_id)

        data = GuildData(guild).__dict__
        del data['Guild']

        if bot.db.add_guild_table(guild.id, data):
            await channel.send(embed=discord.Embed(description=f"Guild \"{guild.name}\" added to database."))
        else:
            await channel.send(embed=discord.Embed(description=f"Guild \"{guild.name}\" already in database."))
        return

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        # prep sending notif to Glass Harbor (for logging/debug)
        glass_guild = bot.get_guild(GLASS_HARBOR)
        chan_id = bot.db.get_channel_logs(glass_guild.id)
        channel = get(glass_guild.text_channels, id=chan_id)

        if bot.db.drop_guild_table(guild.id):
            await channel.send(embed=discord.Embed(description=f"Guild \"{guild.name}\" removed from database."))
        else:
            await channel.send(embed=discord.Embed(description=f"Guild \"{guild.name}\" not found in database."))
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
        from PIL import Image
        import io
        import httpx

        guild = member.guild
        channel_id = bot.db.get_channel_welcome(guild_id=guild.id)
        if channel_id == 0:
            return
        channel = get(guild.text_channels, id=channel_id) 
        

        av = httpx.get(member.display_avatar.url)
        ocean = Image.open(f'{cog_path.parent.parent.parent}/docs/images/welcome_background.png')
        pfp = Image.open(io.BytesIO(av.content))
        pfp = pfp.resize((650,650))
        
        ocean_w, ocean_h = ocean.size
        pfp_w, pfp_h = pfp.size
        offset = ((ocean_w - pfp_w) // 2, (ocean_h - pfp_h) // 2)
                        
        base = Image.new('RGBA', ocean.size)
        base.paste(pfp, offset)
        
        img = Image.alpha_composite(base, ocean)

        with io.BytesIO() as image_binary:
            img.save(image_binary, 'PNG')
            image_binary.seek(0)
            await channel.send(
                content=f"Welcome, {member.mention}!",
                embed=discord.Embed(
                    title=f"Welcome to {guild.name}",
                    description=f"""
                    Please familiarize yourself with the Harbor <#954197139049816066>, 
                    have a look around, and enjoy your stay!

                    If you have any questions or concerns, feel free to mention the crew: <@&408812277836283908>/<@&428800694439641091>.
                    """
                ),
                file=discord.File(fp=image_binary, filename='image.png')
            )