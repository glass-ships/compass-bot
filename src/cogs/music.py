import discord
from discord.ext import commands

from random import choice
import asyncio

from music import music_utils
from music.playback import Timer, Origins
from utils.bot_config import EMBED_COLORS
from music.music_config import *

from utils.log_utils import get_logger
logger = get_logger(f"compass.{__name__}")

### Setup Cog

async def setup(bot):
    await bot.add_cog(Music(bot))


class Music(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")

    @commands.command(name='play', description=HELP_PLAY, aliases=['p'])
    async def _add_to_queue(self, ctx, *, input: str):

        # Get MusicPlayer for guild
        current_guild = music_utils.get_guild(self.bot, ctx.message)
        player = music_utils.guild_player[current_guild]

        # if not await self.checks(ctx, input):
        #     return
        
        # Reset time-out timer
        player.timer.cancel()
        player.timer = Timer(player.timeout_handler)

        # Alert if loop enabled
        if player.queue.loop == True:
            await ctx.send("Loop is enabled! Use {}loop to disable".format(self.bot.db.get_prefix(current_guild)))
            return

        # get queue before adding (send now playing if empty at first)
        current_queue = len(player.queue.playque)
        
        # Process/play song
        song = await player.process_song(ctx, track=input)
        
        if song is None:
            await ctx.send(SONGINFO_ERROR)
            return

        # Send a "queued" message if not the first song
        if song.origin == Origins.Default:
            if player.current_song != None and len(player.queue.playque) != 0:
                await ctx.send(embed=song.format_output(SONGINFO_QUEUE_ADDED, pos=current_queue+1))
        elif song.origin == Origins.Playlist:
            await ctx.send(embed=discord.Embed(description=f"{SONGINFO_PLAYLIST_QUEUED}", color=choice(EMBED_COLORS)))    

    @commands.command(name='songinfo', description=HELP_SONGINFO, aliases=["np", 'nowplaying', 'song'])
    async def _songinfo(self, ctx):
        current_guild = music_utils.get_guild(self.bot, ctx.message)

        if await music_utils.play_check(ctx) == False:
            return

        if current_guild is None:
            await ctx.send(NO_GUILD_MESSAGE)
            return
        song = music_utils.guild_player[current_guild].current_song
        if song is None:
            return
        await ctx.send(embed=song.format_output(SONGINFO_NOW_PLAYING))

    @commands.command(name='queue', description=HELP_QUEUE, aliases=['playlist', 'q'])
    async def _queue(self, ctx):
        current_guild = music_utils.get_guild(self.bot, ctx.message)

        if await music_utils.play_check(ctx) == False:
            return

        if current_guild is None:
            await ctx.send(NO_GUILD_MESSAGE)
            return
        
        queue = music_utils.guild_player[current_guild].queue.playque
        if (
                current_guild.voice_client is None or 
                not current_guild.voice_client.is_playing() or
                len(queue) == 0
            ):
            await ctx.send(":jar: Queue is empty!")
            return

        queue_list = []
        for counter, song in enumerate(list(queue), start=1):
            if song.title is None:
                queue_entry = f"{counter}. [{song.webpage_url}]({song.webpage_url})"
            else:
                queue_entry = f"{counter}. [{song.title}]({song.webpage_url})"
            
            queue_str = "\n".join(queue_list)
            if len(queue_str) + len(queue_entry) < 4096 and len(queue_list) < 20:
                queue_list.append(queue_entry)
            else:
                break

        embed = discord.Embed(title="<:_playlist:1011048129111543880> Queue", color=choice(EMBED_COLORS))
        embed.description="\n".join(queue_list)
        embed.set_footer(
            text=f"Plus {len(queue)-counter} more queued..."
        )

        await ctx.send(embed=embed)

    @commands.command(name='history', description=HELP_HISTORY, aliases=['hist', 'h'])
    async def _history(self, ctx):
        current_guild = music_utils.get_guild(self.bot, ctx.message)

        if await music_utils.play_check(ctx) == False:
            return

        if current_guild is None:
            await ctx.send(NO_GUILD_MESSAGE)
            return
        await ctx.send(music_utils.guild_player[current_guild].track_history())

    @commands.command(name='skip', description=HELP_SKIP, aliases=['s'])
    async def _skip(self, ctx):
        current_guild = music_utils.get_guild(self.bot, ctx.message)

        if await music_utils.play_check(ctx) == False:
            return

        player = music_utils.guild_player[current_guild]
        player.queue.loop = False

        player.timer.cancel()
        player.timer = Timer(player.timeout_handler)

        if current_guild is None:
            await ctx.send(NO_GUILD_MESSAGE)
            return

        if current_guild.voice_client is None or (
                not current_guild.voice_client.is_paused() and not current_guild.voice_client.is_playing()):
            await ctx.send(":jar: Queue is empty!")
            return

        current_guild.voice_client.stop()

    @commands.command(name='prev', description=HELP_PREV, aliases=['back'])
    async def _prev(self, ctx):
        current_guild = music_utils.get_guild(self.bot, ctx.message)

        if await music_utils.play_check(ctx) == False:
            return

        player = music_utils.guild_player[current_guild]
        player.queue.loop = False

        player.timer.cancel()
        player.timer = Timer(player.timeout_handler)

        if current_guild is None:
            await ctx.send(NO_GUILD_MESSAGE)
            return
        await music_utils.guild_player[current_guild].prev_song()
        await ctx.send(":track_previous: Playing previous song")

    @commands.command(name='skipto', description=HELP_SKIPTO, aliases=['goto'])
    async def _skip_to(self, ctx, position: int):
        pass

    @commands.command(name='move', description=HELP_MOVE, aliases=['mv'])
    async def _move(self, ctx, oldposition: int, newposition: int):
        
        current_guild = music_utils.get_guild(self.bot, ctx.message)
        player = music_utils.guild_player[current_guild]
        
        # could this just be "if len(playque) == 0" ???
        if current_guild.voice_client is None or (not current_guild.voice_client.is_paused() and not current_guild.voice_client.is_playing()):
            await ctx.send(":hole: Queue is empty!")
            return
            
        song = player.queue.playque[oldposition-1]
        if song.title is None:
            songname = f"[{song.webpage_url}]({song.webpage_url})"
        else:
            songname = f"[{song.title}]({song.webpage_url})"

        try:
            player.queue.move(oldposition - 1, newposition - 1)
        except IndexError:
            await ctx.send("Invalid selection")
            return
        await ctx.send(embed=discord.Embed(description=f"Moved track to position {newposition}: {songname}"))

    @commands.command(name='remove', description=HELP_REMOVE, aliases=['rm', 'del', 'delete'])
    async def _remove(self, ctx, position: int):
        current_guild = music_utils.get_guild(self.bot, ctx.message)
        player = music_utils.guild_player[current_guild]
        
        queue = player.queue.playque
        song = queue[position-1]
        if song.title is None:
            songname = f"{position}. [{song.webpage_url}]({song.webpage_url})"
        else:
            songname = f"{position}. [{song.title}]({song.webpage_url})"
        
        try:
            del queue[position-1]
            msg = f"Removed track from queue: {songname}"
        except Exception as e:
            msg = f"Error: Couldn't remove track from queue: {songname}\n```\n\n{e}\n```"
        await ctx.send(embed=discord.Embed(description=msg))

    @commands.command(name='shuffle', description=HELP_SHUFFLE, aliases=["sh"])
    async def _shuffle(self, ctx):
        current_guild = music_utils.get_guild(self.bot, ctx.message)
        player = music_utils.guild_player[current_guild]

        if await music_utils.play_check(ctx) == False:
            return

        if current_guild is None:
            await ctx.send(NO_GUILD_MESSAGE)
            return
        if current_guild.voice_client is None or not current_guild.voice_client.is_playing():
            await ctx.send(":hole: Queue is empty!")
            return

        player.queue.shuffle()
        await ctx.send(":twisted_rightwards_arrows: Queue shuffled ")

        for song in list(player.queue.playque)[:MAX_SONG_PRELOAD]:
            asyncio.ensure_future(player.preload(song))

    @commands.command(name='loop', description=HELP_LOOP, aliases=['l', 'repeat'])
    async def _loop(self, ctx):
        return            
        current_guild = music_utils.get_guild(self.bot, ctx.message)
        player = music_utils.guild_player[current_guild]

        if await music_utils.play_check(ctx) == False:
            return

        if len(player.queue.playque) < 1 and current_guild.voice_client.is_playing() == False:
            await ctx.send("No songs in queue!")
            return

        if player.queue.loop == False:
            player.queue.loop = True
            await ctx.send("<:retweet:1011048385534496862> Loop enabled")
        else:
            player.queue.loop = False
            await ctx.send(":arrow_right: Loop disabled")

    @commands.command(name='pause', description=HELP_PAUSE)
    async def _pause(self, ctx):
        current_guild = music_utils.get_guild(self.bot, ctx.message)

        if await music_utils.play_check(ctx) == False:
            return

        if current_guild is None:
            await ctx.send(NO_GUILD_MESSAGE)
            return
        if current_guild.voice_client is None or not current_guild.voice_client.is_playing():
            return
        current_guild.voice_client.pause()
        await ctx.send("Playback Paused :pause_button:")

    @commands.command(name='resume', description=HELP_RESUME)
    async def _resume(self, ctx):
        current_guild = music_utils.get_guild(self.bot, ctx.message)

        if await music_utils.play_check(ctx) == False:
            return

        if current_guild is None:
            await ctx.send(NO_GUILD_MESSAGE)
            return
        current_guild.voice_client.resume()
        await ctx.send(":arrow_forward: Resumed playback")

    @commands.command(name='stop', description=HELP_STOP)
    async def _stop(self, ctx):

        if await music_utils.play_check(ctx) == False:
            return

        current_guild = music_utils.get_guild(self.bot, ctx.message)
        player = music_utils.guild_player[current_guild]
        player.queue.loop = False
        await music_utils.guild_player[current_guild].stop_player()

        # if current_guild is None:
        #     await ctx.send(NO_GUILD_MESSAGE)
        #     return
        await ctx.send(":x: Stopped.")

    @commands.command(name='clear', description=HELP_CLEAR)
    async def _clear(self, ctx):
        current_guild = music_utils.get_guild(self.bot, ctx.message)

        if await music_utils.play_check(ctx) == False:
            return

        player = music_utils.guild_player[current_guild]
        player.clear_queue()
        current_guild.voice_client.stop()
        player.queue.loop = False
        await ctx.send(":jar: Cleared queue.")

    @commands.command(name='leave')
    async def _disconnect(self, ctx):
        current_guild = music_utils.get_guild(self.bot, ctx.message)

        

        await music_utils.guild_player[current_guild].udisconnect()

    @commands.command(name='volume', description=HELP_VOL, aliases=["vol"])
    async def _volume(self, ctx, *args):

        if ctx.guild is None:
            await ctx.send(NO_GUILD_MESSAGE)
            return

        if await music_utils.play_check(ctx) == False:
            return

        if len(args) == 0:
            await ctx.send(":speaker: Current volume: {}%".format(music_utils.guild_player[ctx.guild]._volume))
            return

        try:
            volume = args[0]
            volume = int(volume)
            if volume > 100 or volume < 0:
                raise Exception('')
            current_guild = music_utils.get_guild(self.bot, ctx.message)

            if music_utils.guild_player[current_guild]._volume >= volume:
                await ctx.send(':sound: Volume set to {}%'.format(str(volume)))
            else:
                await ctx.send(':loud_sound: Volume set to {}%'.format(str(volume)))
            music_utils.guild_player[current_guild].volume = volume
        except:
            await ctx.send("Error: Volume must be a number 1-100")

