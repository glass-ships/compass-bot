import asyncio
from loguru import logger

import discord
from discord import app_commands
from discord.ext import commands

from compass_bot.music import music_utils
from compass_bot.music.player import Timer
from compass_bot.music.music_config import ErrorMessages, InfoMessages, MAX_SONG_PRELOAD
from compass_bot.utils.bot_config import EMBED_COLOR, Emojis


### Helpers and Checks ###


async def get_player(itx: discord.Interaction):
    """Get MusicPlayer for guild"""
    # TODO: maybe create player if one doesn't exist?

    player = music_utils.guild_player[itx.guild]
    if player is None:
        await itx.followup.send("ERROR: No Player found for this guild.")
        raise AttributeError

    # Reset timer
    player.timer.stop()
    player.timer = Timer(player.timeout_handler)

    return player


async def _play_check(itx: discord.Interaction):  # , player):
    """Check necessary conditions for music commands"""

    ##### Possibly unnecessary, due to native app management in Discord ##################################
    # Check that command was sent in music channel, if applicable
    music_channel = bot.db.get_channel_music(itx.guild.id)
    if music_channel is not None and music_channel != itx.channel_id:
        await itx.followup.send(f"ERROR: Please use in the designated music channel: <#{music_channel}>")
        return False
    ######################################################################################################

    # Check that command was sent in a guild
    if itx.guild is None:
        await itx.response.send_message(ErrorMessages.NO_GUILD)
        return

    player = await get_player(itx)

    # Check user is in a VC
    user_vc = await player.get_user_vc(itx)
    if user_vc is None:
        await itx.followup.send(embed=discord.Embed(description=ErrorMessages.NO_USER_VC, color=EMBED_COLOR()))
        return False

    # Connect bot to VC
    bot_vc = await player.get_bot_vc(bot, itx)
    if bot_vc is None:
        await player.connect(itx, user_vc)
    elif bot_vc == user_vc:
        logger.debug(f"Already connected: {bot_vc.name}")
    else:
        await itx.followup.send(
            embed=discord.Embed(description=ErrorMessages.WRONG_USER_VC(bot_vc), color=EMBED_COLOR())
        )
        return False

    return True


play_check = app_commands.check(_play_check)

### Setup Cog ###


async def setup(bot):
    await bot.add_cog(Music(bot))


class Music(commands.Cog):
    def __init__(self, bot_: commands.Bot):
        global bot
        bot = bot_

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")

    ##################
    # Slash Commands #
    ##################

    @play_check
    @app_commands.command(name="play", description="Play a song or playlist (keyword search or supported link).")
    async def _add_to_queue(self, itx: discord.Interaction, *, query: str):
        await itx.response.defer()
        player = await get_player(itx)
        if not await _play_check(itx):
            return
        await player.process_request(itx, query)
        return

    @play_check
    @app_commands.command(name="queue", description="Show the current queue.")
    async def _queue(self, itx: discord.Interaction):
        await itx.response.defer()
        player = await get_player(itx)
        await itx.followup.send(embed=player.queue.queue_embed())
        return

    @play_check
    @app_commands.command(name="pause", description="Pause playback (continue with `/resume`).")
    async def _pause(self, itx: discord.Interaction):
        await itx.response.defer()
        if itx.guild.voice_client is None or not itx.guild.voice_client.is_playing():  # type: ignore
            return
        itx.guild.voice_client.pause()  # type: ignore
        await itx.followup.send(f"{Emojis.pause} Playback Paused")
        return

    @play_check
    @app_commands.command(name="resume", description="Resume playback.")
    async def _resume(self, itx: discord.Interaction):
        itx.guild.voice_client.resume()  # type: ignore
        await itx.response.send_message(f"{Emojis.musicNote} Resumed playback")
        return

    @play_check
    @commands.command(name="nowplaying", description="Show info about current song.")
    async def _songinfo(self, itx: discord.Interaction):
        if not await _play_check(itx):
            return

        song = music_utils.guild_player[itx.guild].current_song
        if song is None:
            await itx.response.send(InfoMessages.NOT_PLAYING)
            return
        await itx.response.send(embed=song.now_playing_embed())
        return

    ############################################################################################################

    @app_commands.command(name="history", description="Show the last 10 songs played.")
    async def _history(self, itx: discord.Interaction):
        await itx.response.send_message(music_utils.guild_player[itx.guild].track_history())

    @app_commands.command(name="skip", description="Skip the current song")
    async def _skip(self, itx: discord.Interaction):
        await itx.response.defer()
        player = music_utils.guild_player[itx.guild]
        player.queue.loop = False

        # await player.timer.restart()
        player.timer.stop()
        player.timer = Timer(player.timeout_handler)

        if itx.guild.voice_client is None or (  # type: ignore
            not itx.guild.voice_client.is_paused() and not itx.guild.voice_client.is_playing()  # type: ignore
        ):
            await itx.response.send_message(InfoMessages.QUEUE_EMPTY)
            return

        itx.guild.voice_client.stop()  # type: ignore
        await itx.followup.send(f"Skipped")

    @commands.command(name="prev", description="Play the previous song again.")
    async def _prev(self, itx: discord.Interaction):
        player = music_utils.guild_player[itx.guild]
        player.queue.loop = False

        player.timer.stop()
        player.timer = Timer(player.timeout_handler)
        # await player.timer.restart()

        await music_utils.guild_player[itx.guild].prev_song()
        await itx.response.send_message(f"{Emojis.previous} Playing previous song")

    @commands.command(name="skipto", description="Skips to the specified position in the queue")
    async def _skip_to(self, itx, position: int):
        pass

    @commands.command(name="move", description="Move a track in the queue.")
    async def _move(self, itx, oldposition: int, newposition: int):
        player = music_utils.guild_player[itx.guild]

        # could this just be "if len(playque) == 0" ???
        if itx.guild.voice_client is None or (
            not itx.guild.voice_client.is_paused() and not itx.guild.voice_client.is_playing()
        ):
            await itx.response.send_message(InfoMessages.QUEUE_EMPTY)
            return

        song = player.queue.playque[oldposition - 1]
        if song.title is None:
            songname = f"[{song.webpage_url}]({song.webpage_url})"
        else:
            songname = f"[{song.title}]({song.webpage_url})"

        try:
            player.queue.move(oldposition - 1, newposition - 1)
        except IndexError:
            await itx.response.send_message("Invalid selection")
            return
        await itx.response.send_message(
            embed=discord.Embed(description=f"Moved track to position {newposition}: {songname}")
        )

    @commands.command(name="remove", description="Remove the song at the given index.")
    async def _remove(self, itx, position: int):
        player = music_utils.guild_player[itx.guild]

        queue = player.queue.playque
        song = queue[position - 1]
        if song.title is None:
            songname = f"{position}. [{song.webpage_url}]({song.webpage_url})"
        else:
            songname = f"{position}. [{song.title}]({song.webpage_url})"

        try:
            del queue[position - 1]
            msg = f"Removed track from queue: {songname}"
        except Exception as e:
            msg = f"Error: Couldn't remove track from queue: {songname}\n```\n\n{e}\n```"
        await itx.response.send_message(embed=discord.Embed(description=msg))

    @commands.command(name="shuffle", description="Shuffle the queue (irreversible!)")
    async def _shuffle(self, itx: discord.Interaction):
        player = music_utils.guild_player[itx.guild]

        if itx.guild.voice_client is None or not itx.guild.voice_client.is_playing():  # type: ignore
            await itx.response.send_message(InfoMessages.QUEUE_EMPTY)
            return

        player.queue.shuffle()
        await itx.response.send_message(f"{Emojis.shuffle} Queue shuffled ")

        for song in list(player.queue.playque)[:MAX_SONG_PRELOAD]:
            asyncio.ensure_future(player.preload(song))

    @commands.command(name="loop", description="Loop the currently playing song and locks the queue. Toggle on/off.")
    async def _loop(self, itx: discord.Interaction):
        return

        player = music_utils.guild_player[itx.guild]

        if len(player.queue.playque) < 1 and itx.guild.voice_client.is_playing() is False:
            await itx.response.send_message("No songs in queue!")
            return

        if player.queue.loop is False:
            player.queue.loop = True
            await itx.response.send_message(f"{Emojis.loop} Loop enabled")
        else:
            player.queue.loop = False
            await itx.response.send_message(":arrow_right: Loop disabled")

    # @commands.command(name='pause', description="Pause playback (continue with `/resume`).")
    # async def _pause(self, itx: discord.Interaction):

    #     if itx.guild.voice_client is None or not itx.guild.voice_client.is_playing():
    #         return
    #     itx.guild.voice_client.pause()
    #     await itx.response.send_message("Playback Paused :pause_button:")

    # @commands.command(name='resume', description="Resume playback.")
    # async def _resume(self, itx: discord.Interaction):

    #     itx.guild.voice_client.resume()
    #     await itx.response.send_message(":arrow_forward: Resumed playback")

    @commands.command(name="stop", description="Clear the queue and stop playback.")
    async def _stop(self, itx: discord.Interaction):
        player = await self.get_player(itx)
        player.queue.loop = False

        player.timer.stop()
        player.timer = Timer(player.timeout_handler)
        # await player.timer.restart()
        await player.stop_player()

        await itx.response.send_message(":x: Stopped.")
        return

    @commands.command(name="clear", description="Clear the queue and skips the current song.")
    async def _clear(self, itx: discord.Interaction):
        player = await self.get_player(itx)
        player.clear_queue()
        player.queue.loop = False

        player.timer.stop()
        player.timer = Timer(player.timeout_handler)
        # await player.timer.restart()
        await itx.response.send_message(InfoMessages.QUEUE_CLEARED)
        return

    @commands.command(name="join", description="Move Compass to the user's VC")
    async def _join_vc(self, itx: discord.Interaction):
        pass

    @app_commands.command(name="leave", description="Disconnect bot from VC.")
    async def _disconnect(self, itx: discord.Interaction):
        player = await get_player(itx)
        await player.disconnect()
        await itx.response.send_message("Disconnected.")
        return
