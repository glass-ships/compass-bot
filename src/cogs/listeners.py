##### Cog - Listeners #####

### Imports ###

import discord
from discord.ext import commands
from discord.utils import get

import time

from helper import * 

### Setup Cog

# Startup method
async def setup(bot):
    await bot.add_cog(Listeners(bot))

# Define Class
class Listeners(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Cog Online: {self.qualified_name}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """A global error handler cog."""

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
        else:
            message = f"Oh no! Something went wrong while running the command!\n```\n{error}\n```"

        await ctx.send(message, delete_after=5)
        await ctx.message.delete(delay=5)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """
        When a mod reacts to any message with the :mag: emoji,
        Bot will flag the message and send the info to a logs channel
        """
        if str(reaction.emoji) == '🔍':                        
            mod_roles = self.bot.db.get_mod_roles(reaction.message.guild.id)
            roles = [x.id for x in user.roles]
            if any(mr in roles for mr in mod_roles):
                # Remove the reaction           
                await reaction.message.remove_reaction('🔍', user)

                # Get info
                flagger = user
                flagged_message, flagged_user = reaction.message, reaction.message.author
                dt = datetime.now()
                flagged_time = int(time.mktime(dt.timetuple()))

                # Create embed
                ce = discord.Embed(
                    title=f"Flagged Message",
                    description=f"A message has been flagged in {flagged_message.channel}"
                )
                ce.add_field(name="Message content:",
                            value=flagged_message.content,
                            inline=False
                )           
                ce.add_field(name="Flagged by:", value=flagger, inline=True)
                ce.add_field(name="Message Author:", value=flagged_user, inline=True)
                ce.add_field(name="Message:", value=f"[Jump to](https://discordapp.com/channels/{flagged_message.guild.id}/{flagged_message.channel.id}/{flagged_message.id})", inline=True)
                for i in flagged_message.attachments:
                    ce.add_field(name="Attachment:", value=f"{i.filename})")
                ce.add_field(name="Flagged at:", value=f"<t:{flagged_time}:R>")

                # Send embed to logs
                channel_id = self.bot.db.get_channel_logs(flagged_message.guild.id)
                channel = get(flagged_message.guild.text_channels, id=channel_id)
                await channel.send(content=None, embed=ce)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):

        # prep sending notif to Glass Harbor (for logging/debug)
        glass_guild = get_guild(self.bot, 393995277713014785)
        chan_id = self.bot.db.get_channel_logs(glass_guild.id)
        channel = get(glass_guild.text_channels, id=chan_id)

        if guild.system_channel:
            default_channel = guild.system_channel.id
        else:
            default_channel = None
        
        # put together default data
        data = {"guild_id":guild.id,"guild_name":guild.name,"mod_roles":[],"chan_announce":default_channel,"chan_bot":default_channel,"chan_logs":default_channel,"prefix":";"}

        if self.bot.db.add_guild_table(guild.id, data):
            await channel.send(f"Guild \"{guild.name}\" added to database.")
        else:
            await channel.send(f"Guild \"{guild.name}\" already in database.")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):

        # prep sending notif to Glass Harbor (for logging/debug)
        glass_guild = get_guild(self.bot, 393995277713014785)
        chan_id = self.bot.db.get_channel_logs(glass_guild.id)
        channel = get(glass_guild.text_channels, id=chan_id)

        guild_id = guild.id

        if self.bot.db.drop_guild_table(guild_id):
            await channel.send(f"Guild \"{guild.name}\" removed from database.")
        else:
            await channel.send(f"Guild \"{guild.name}\" not found in database.")

    @commands.Cog.listener()
    async def on_guild_update(self, oldguild, newguild):
        self.bot.db.update_guild_name(oldguild.id, newguild.name)
