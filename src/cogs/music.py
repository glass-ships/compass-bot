### Imports ###

import discord
from discord.ext import commands
from discord.utils import get
#from distutils.command.config import config

from random import choice
#import aiohttp, yt_dlp
#from email.mime import audio

from utils.helper import * 
import utils.music_config as config
import utils.music_utils as utils


logger = get_logger(__name__)

### Setup Cog

# Startup method
async def setup(bot):
    await bot.add_cog(Music(bot))
    

# Define Class
class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _get_prefix(self, ctx):
        return self.bot.db.get_prefix(ctx.message.guild.id)

    def _get_prefix_itx(self, itx):
        return self.bot.db.get_prefix(itx.guild_id)

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")

    @commands.command(name='play', description=config.HELP_PLAY, aliases=['p'])
    async def _play_song(self, ctx, *, track: str):

        # Get audio controller for guild
        current_guild = get_guild(self.bot, ctx.message)
        audiocontroller = utils.guild_audiocontroller[current_guild]

        if (await utils.is_connected(ctx) == None):
            if await audiocontroller.uconnect(ctx) == False:
                return
        
        # Make sure command isn't empty
        if track.isspace() or not track:
            return

        # Checks that user is in a VC, and command was sent in appropriate channel
        if await utils.play_check(ctx) == False:
            return

        # Reset time-out timer
        audiocontroller.timer.cancel()
        audiocontroller.timer = utils.Timer(audiocontroller.timeout_handler)

        # Alert if loop enabled
        if audiocontroller.queue.loop == True:
            await ctx.send("Loop is enabled! Use {}loop to disable".format(self.bot.db.get_prefix(current_guild)))
            return

        # get queue before adding (send now playing if empty at first)
        current_queue = len(audiocontroller.queue.playque)
        
        # Process/play song
        song = await audiocontroller.process_song(ctx,  track=track) #session=self.session,)
        
        if song is None:
            await ctx.send(config.SONGINFO_ERROR)
            return

        # Send a "queued" message if not the first song
        if song.origin == utils.Origins.Default:
            if audiocontroller.current_song != None and len(audiocontroller.queue.playque) != 0:
                await ctx.send(embed=song.info.format_output(config.SONGINFO_QUEUE_ADDED, pos=current_queue+1))
        elif song.origin == utils.Origins.Playlist:
            await ctx.send(embed=discord.Embed(description=f"{config.SONGINFO_PLAYLIST_QUEUED}", color=choice(config.EMBED_COLORS)))    

    @commands.command(name='songinfo', description=config.HELP_SONGINFO, aliases=["np", 'nowplaying', 'song'])
    async def _songinfo(self, ctx):
        current_guild = get_guild(self.bot, ctx.message)

        if await utils.play_check(ctx) == False:
            return

        if current_guild is None:
            await ctx.send(config.NO_GUILD_MESSAGE)
            return
        song = utils.guild_audiocontroller[current_guild].current_song
        if song is None:
            return
        await ctx.send(embed=song.info.format_output(config.SONGINFO_NOW_PLAYING))

    @commands.command(name='queue', description=config.HELP_QUEUE, aliases=['playlist', 'q'])
    async def _queue(self, ctx):
        current_guild = get_guild(self.bot, ctx.message)

        if await utils.play_check(ctx) == False:
            return

        if current_guild is None:
            await ctx.send(config.NO_GUILD_MESSAGE)
            return
        if current_guild.voice_client is None or not current_guild.voice_client.is_playing():
            await ctx.send(":hole: Queue is empty!")
            return

        queue = utils.guild_audiocontroller[current_guild].queue.playque
        embed = discord.Embed(title="<:playlist:986751164274049044> Queue", color=choice(config.EMBED_COLORS))

        queue_list = []
        for counter, song in enumerate(list(queue), start=1):
            if song.info.title is None:
                queue_entry = f"{counter}. [{song.info.webpage_url}]({song.info.webpage_url})"
            else:
                queue_entry = f"{counter}. [{song.info.title}]({song.info.webpage_url})"
            
            queue_str = "\n".join(queue_list)
            if len(queue_str) + len(queue_entry) < 4096 and len(queue_list) < 20:
                queue_list.append(queue_entry)
            else:
                break
        embed.description="\n".join(queue_list)
        embed.set_footer(
            text=f"Plus {len(queue)-counter} more queued..."
        )

        await ctx.send(embed=embed)

    @commands.command(name='history', description=config.HELP_HISTORY, aliases=['hist', 'h'])
    async def _history(self, ctx):
        current_guild = get_guild(self.bot, ctx.message)

        if await utils.play_check(ctx) == False:
            return

        if current_guild is None:
            await ctx.send(config.NO_GUILD_MESSAGE)
            return
        await ctx.send(utils.guild_audiocontroller[current_guild].track_history())

    @commands.command(name='skip', description=config.HELP_SKIP, aliases=['s'])
    async def _skip(self, ctx):
        current_guild = get_guild(self.bot, ctx.message)

        if await utils.play_check(ctx) == False:
            return

        audiocontroller = utils.guild_audiocontroller[current_guild]
        audiocontroller.queue.loop = False

        audiocontroller.timer.cancel()
        audiocontroller.timer = utils.Timer(audiocontroller.timeout_handler)

        if current_guild is None:
            await ctx.send(config.NO_GUILD_MESSAGE)
            return

        if current_guild.voice_client is None or (
                not current_guild.voice_client.is_paused() and not current_guild.voice_client.is_playing()):
            await ctx.send(":hole: Queue is empty!")
            return

        current_guild.voice_client.stop()

        await asyncio.sleep(1.0)        
        await ctx.send(embed=audiocontroller.current_song.info.format_output(config.SONGINFO_NOW_PLAYING))

    @commands.command(name='prev', description=config.HELP_PREV, aliases=['back'])
    async def _prev(self, ctx):
        current_guild = get_guild(self.bot, ctx.message)

        if await utils.play_check(ctx) == False:
            return

        audiocontroller = utils.guild_audiocontroller[current_guild]
        audiocontroller.queue.loop = False

        audiocontroller.timer.cancel()
        audiocontroller.timer = utils.Timer(audiocontroller.timeout_handler)

        if current_guild is None:
            await ctx.send(config.NO_GUILD_MESSAGE)
            return
        await utils.guild_audiocontroller[current_guild].prev_song()
        await ctx.send(":track_previous: Playing previous song")

    @commands.command(name='skipto', description=config.HELP_SKIPTO, aliases=['goto'])
    async def _skip_to(self, ctx):
        pass

    @commands.command(name='move', description=config.HELP_MOVE, aliases=['mv'])
    async def _move(self, ctx, oldindex: int, newindex: int):
        
        current_guild = get_guild(self.bot, ctx.message)
        audiocontroller = utils.guild_audiocontroller[current_guild]
        
        # could this just be "if len(playque) == 0" ???
        if current_guild.voice_client is None or (not current_guild.voice_client.is_paused() and not current_guild.voice_client.is_playing()):
            await ctx.send(":hole: Queue is empty!")
            return
            
        song = audiocontroller.queue.playque[oldindex-1]
        if song.info.title is None:
            songname = f"[{song.info.webpage_url}]({song.info.webpage_url})"
        else:
            songname = f"[{song.info.title}]({song.info.webpage_url})"

        try:
            audiocontroller.queue.move(oldindex - 1, newindex - 1)
        except IndexError:
            await ctx.send("Invalid selection")
            return
        await ctx.send(embed=discord.Embed(description=f"Moved track to position {newindex}: {songname}"))

    @commands.command(name='remove', description=config.HELP_REMOVE, aliases=['rm', 'del', 'delete'])
    async def _remove(self, ctx, index: int):
        current_guild = get_guild(self.bot, ctx.message)
        audiocontroller = utils.guild_audiocontroller[current_guild]
        
        queue = audiocontroller.queue.playque
        song = queue[index-1]
        if song.info.title is None:
            songname = f"{index}. [{song.info.webpage_url}]({song.info.webpage_url})"
        else:
            songname = f"{index}. [{song.info.title}]({song.info.webpage_url})"
        
        try:
            del queue[index-1]
            msg = f"Removed track from queue: {songname}"
        except Exception as e:
            msg = f"Error: Couldn't remove track from queue: {songname}\n```\n\n{e}\n```"
        await ctx.send(embed=discord.Embed(description=msg))

    @commands.command(name='shuffle', description=config.HELP_SHUFFLE, aliases=["sh"])
    async def _shuffle(self, ctx):
        current_guild = get_guild(self.bot, ctx.message)
        audiocontroller = utils.guild_audiocontroller[current_guild]

        if await utils.play_check(ctx) == False:
            return

        if current_guild is None:
            await ctx.send(config.NO_GUILD_MESSAGE)
            return
        if current_guild.voice_client is None or not current_guild.voice_client.is_playing():
            await ctx.send(":hole: Queue is empty!")
            return

        audiocontroller.queue.shuffle()
        await ctx.send(":twisted_rightwards_arrows: Queue shuffled ")

        for song in list(audiocontroller.queue.playque)[:config.MAX_SONG_PRELOAD]:
            asyncio.ensure_future(audiocontroller.preload(song))#self.session, song))

    @commands.command(name='loop', description=config.HELP_LOOP, aliases=['l', 'repeat'])
    async def _loop(self, ctx):
        return            
        current_guild = get_guild(self.bot, ctx.message)
        audiocontroller = utils.guild_audiocontroller[current_guild]

        if await utils.play_check(ctx) == False:
            return

        if len(audiocontroller.queue.playque) < 1 and current_guild.voice_client.is_playing() == False:
            await ctx.send("No songs in queue!")
            return

        if audiocontroller.queue.loop == False:
            audiocontroller.queue.loop = True
            await ctx.send("<:retweet:964692541779898430> Loop enabled")
        else:
            audiocontroller.queue.loop = False
            await ctx.send(":arrow_right: Loop disabled")

    @commands.command(name='pause', description=config.HELP_PAUSE)
    async def _pause(self, ctx):
        current_guild = get_guild(self.bot, ctx.message)

        if await utils.play_check(ctx) == False:
            return

        if current_guild is None:
            await ctx.send(config.NO_GUILD_MESSAGE)
            return
        if current_guild.voice_client is None or not current_guild.voice_client.is_playing():
            return
        current_guild.voice_client.pause()
        await ctx.send("Playback Paused :pause_button:")

    @commands.command(name='resume', description=config.HELP_RESUME)
    async def _resume(self, ctx):
        current_guild = get_guild(self.bot, ctx.message)

        if await utils.play_check(ctx) == False:
            return

        if current_guild is None:
            await ctx.send(config.NO_GUILD_MESSAGE)
            return
        current_guild.voice_client.resume()
        await ctx.send(":arrow_forward: Resumed playback")

    @commands.command(name='stop', description=config.HELP_STOP, aliases=['st'])
    async def _stop(self, ctx):
        current_guild = get_guild(self.bot, ctx.message)

        if await utils.play_check(ctx) == False:
            return

        audiocontroller = utils.guild_audiocontroller[current_guild]
        audiocontroller.queue.loop = False
        if current_guild is None:
            await ctx.send(config.NO_GUILD_MESSAGE)
            return
        await utils.guild_audiocontroller[current_guild].stop_player()
        await ctx.send(":x: Stopped all sessions.")

    @commands.command(name='clear', description=config.HELP_CLEAR, aliases=['cl'])
    async def _clear(self, ctx):
        current_guild = get_guild(self.bot, ctx.message)

        if await utils.play_check(ctx) == False:
            return

        audiocontroller = utils.guild_audiocontroller[current_guild]
        audiocontroller.clear_queue()
        current_guild.voice_client.stop()
        audiocontroller.queue.loop = False
        await ctx.send(":no_entry_sign: Cleared queue.")

    @commands.command(name='volume', description=config.HELP_VOL, aliases=["vol"])
    async def _volume(self, ctx, *args):

        # Check for mod
        mod_roles = self.bot.db.get_mod_roles(ctx.guild.id)
        if not await role_check(ctx, mod_roles):
            return

        if ctx.guild is None:
            await ctx.send(config.NO_GUILD_MESSAGE)
            return

        if await utils.play_check(ctx) == False:
            return

        if len(args) == 0:
            await ctx.send(":speaker: Current volume: {}%".format(utils.guild_audiocontroller[ctx.guild]._volume))
            return

        try:
            volume = args[0]
            volume = int(volume)
            if volume > 100 or volume < 0:
                raise Exception('')
            current_guild = get_guild(self.bot, ctx.message)

            if utils.guild_audiocontroller[current_guild]._volume >= volume:
                await ctx.send(':sound: Volume set to {}%'.format(str(volume)))
            else:
                await ctx.send(':loud_sound: Volume set to {}%'.format(str(volume)))
            utils.guild_audiocontroller[current_guild].volume = volume
        except:
            await ctx.send("Error: Volume must be a number 1-100")
