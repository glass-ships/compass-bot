from random import randrange

import discord
from discord.ext import commands
#from discord.utils import get
from loguru import logger

from compass_bot.utils.bot_config import EMBED_COLOR


mode = 1
sendall = False
pins_channel = 948375476685111296 / 954794285222486046

blacklisted_channels = []

### Setup Cog

# Startup method
async def setup(bot):
    await bot.add_cog(PinArchiver(bot))

# Define Class
class PinArchiver(commands.Cog):
    """Archives pins exceeding Discord's limit of 50.

    Mode 1: In mode 1, the most recent pinned message gets sent to a pins archive
    channel of your choice. This means that the most recent pin wont be viewable in
    the pins tab, but will be visible in the pins archive channel that you chose during setup

    Mode 2: In mode 2, the oldest pinned message gets sent to a pins archive channel of
    your choice. This means that the most recent pin will be viewable in the pins tab, and
    the oldest pin will be unpinned and put into the pins archive channel

    Furthermore: the p.sendall feature described later in the code allows the user to set
    Passel so that all pinned messages get sent to the pins archive channel."""
    
    def __init__(self, bot_):
        global bot
        bot = bot_

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")

    # Command to check what the settings of the bot
    @commands.command(name='settings', pass_context=True)
    async def settings(self, ctx):
        if not ctx.message.author.guild_permissions.administrator:
            return

        await ctx.send("The mode you have setup is: " + str(mode))
        await ctx.send("Sendall is toggled to: " + str(sendall))
        await ctx.send("The pins channel for this server is: " + ctx.channel.guild.get_channel(pins_channel).mention)
        await ctx.send("Black listed channels are: ")
        for c in blacklisted_channels:
            try:
                await ctx.send(ctx.channel.guild.get_channel(c).mention)
            except:
                await ctx.send("Error: Check black listed channels")
                return
        await ctx.send("done")


    # The method that takes care of pin updates in a server
    @commands.Cog.listener()
    async def on_guild_channel_pins_update(self, channel, last_pin):
        global data
        try:
            numPins = await channel.pins()

            # checks to see if message is in the blacklist
            # message is only sent if there is a blacklisted server with 50 messages pinned, informs them
            # that passel is in the server and they can un-blacklist the channel to have passel work
            if str(channel.id) in blacklisted_channels:
                return

            isChannelThere = False
            # checks to see if pins channel exists in the server
            channnelList = channel.guild.channels
            for channel in channnelList:
                if int(pins_channel) == int(channel.id):
                    isChannelThere = True

            # checks to see if pins channel exists or has been deleted
            if not isChannelThere:
                await channel.send("Check to see if the pins archive channel during setup has been deleted")
                return

            # only happens if send all is toggled on
            if len(numPins) < 49 and sendall == True:
                last_pinned = numPins[0]
                pinEmbed = discord.Embed(
                    description="\"" + last_pinned.content + "\"",
                    color=EMBED_COLOR()
                )
                # checks to see if pinned message has attachments
                attachments = last_pinned.attachments
                if len(attachments) >= 1:
                    pinEmbed.set_image(url=attachments[0].url)
                pinEmbed.add_field(
                    name="Jump", value=last_pinned.jump_url, inline=False)
                pinEmbed.set_footer(
                    text="sent in: " + last_pinned.channel.name + " - at: " + str(last_pinned.created_at))
                pinEmbed.set_author(name='Sent by ' + last_pinned.author.name)
                await channel.guild.get_channel(int(pins_channel)).send(embed=pinEmbed)
                
                # remove this message if you do not want the bot to send a message when you pin a message
                await last_pinned.channel.send(
                    "See pinned message in " + channel.guild.get_channel(int(pins_channel)).mention)
                return

            # if guild mode is one does the process following mode 1
            if mode == 1:
                last_pinned = numPins[len(numPins) - 1]
                # sends extra messages
                if len(numPins) == 50:
                    last_pinned = numPins[0]
                    pinEmbed = discord.Embed(
                        # title="Sent by " + last_pinned.author.name,
                        description="\"" + last_pinned.content + "\"",
                        color=EMBED_COLOR()
                    )
                    # checks to see if pinned message has attachments
                    attachments = last_pinned.attachments
                    if len(attachments) >= 1:
                        pinEmbed.set_image(url=attachments[0].url)
                    pinEmbed.add_field(
                        name="Jump", value=last_pinned.jump_url, inline=False)
                    pinEmbed.set_footer(
                        text="sent in: " + last_pinned.channel.name + " - at: " + str(last_pinned.created_at))
                    pinEmbed.set_author(name='Sent by ' + last_pinned.author.name)
                    await channel.guild.get_channel(int(pins_channel)).send(embed=pinEmbed)

                    # remove this message if you do not want the bot to send a message when you pin a message
                    await last_pinned.channel.send(
                        "See pinned message in " + channel.guild.get_channel(int(pins_channel)).mention)
                    await last_pinned.unpin()

            # if guild mode is two follows the process for mode 2
            if mode == 2:
                last_pinned = numPins[0]
                if len(numPins) == 50:
                    last_pinned = numPins[len(numPins) - 1]
                    pinEmbed = discord.Embed(
                        # title="Sent by " + last_pinned.author.name,
                        description="\"" + last_pinned.content + "\"",
                        color=EMBED_COLOR()
                    )
                    # checks to see if pinned message has attachments
                    attachments = last_pinned.attachments
                    if len(attachments) >= 1:
                        pinEmbed.set_image(url=attachments[0].url)
                    pinEmbed.add_field(
                        name="Jump", value=last_pinned.jump_url, inline=False)
                    pinEmbed.set_footer(
                        text="sent in: " + last_pinned.channel.name + " - at: " + str(last_pinned.created_at))
                    pinEmbed.set_author(name='Sent by ' + last_pinned.author.name)
                    await last_pinned.guild.get_channel(int(pins_channel)).send(embed=pinEmbed)

                    # remove this message if you do not want the bot to send a message when you pin a message
                    await last_pinned.channel.send(
                        "See oldest pinned message in " + channel.guild.get_channel(int(pins_channel)).mention)
                    await last_pinned.unpin()
        except: # Message was unpinned, do nothing
            pass


    @commands.command(name='pins', pass_context=True)
    async def pins(self, ctx):
        numPins = await ctx.message.channel.pins()
        await ctx.send(ctx.message.channel.mention + " has " + str(len(numPins)) + " pins.")
