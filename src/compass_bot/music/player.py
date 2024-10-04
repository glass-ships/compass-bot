import asyncio

# import aiohttp

import discord
import spotipy
from yt_dlp import YoutubeDL
from loguru import logger

from compass_bot.utils.bot_config import EMBED_COLOR, Emojis, CustomException  # , FetchException, QueueException
from compass_bot.utils.command_utils import send_embed
from compass_bot.utils.utils import extract_url, ddict
from compass_bot.music import music_utils
from compass_bot.music.dataclasses import Playlist, PlaylistTypes, Search, Sites, Song, YouTubeSearchResults
from compass_bot.music.music_config import (
    ErrorMessages,
    InfoMessages,
    COOKIE_PATH,
    VC_TIMEOUT,
    SPOTIFY_ID,
    SPOTIFY_SECRET,
    YTDL_OPTIONS,
)
from compass_bot.music.queue import Queue

# from compass_bot.utils.utils import console


class Timer:
    def __init__(self, callback):
        self._callback = callback
        self._task = asyncio.create_task(self._job())

    async def _job(self):
        await asyncio.sleep(VC_TIMEOUT)
        await self._callback()

    async def restart(self):
        self._task.cancel()
        self._task = asyncio.create_task(self._job())

    def stop(self):
        self._task.cancel()


class MusicPlayer(object):
    """Controls the playback of audio and the sequential playing of the songs.

    Attributes:
        bot: The instance of the bot that will be playing the music.
        queue: A Queue object that stores the history and queue of songs.
        current_song: A Song object that stores details of the current song.
        guild: The guild in which the MusicPlayer operates.
        timer: A Timer object that handles the timeout of the MusicPlayer.
    """

    def __init__(self, bot, guild):
        self.bot = bot
        self.queue = Queue()
        self.current_song = None
        self.vc = None
        self.guild = guild
        self.timer = Timer(self.timeout_handler)

        try:
            sp_creds = spotipy.oauth2.SpotifyClientCredentials(client_id=SPOTIFY_ID, client_secret=SPOTIFY_SECRET)
            self.sp = spotipy.Spotify(client_credentials_manager=sp_creds)
        except Exception as e:
            logger.warning(f"Spotify API Error: {e}")

        if ~discord.opus.is_loaded():
            try:
                discord.opus.load_opus("libopus.so.0")
                logger.debug("Opus successfully loaded")
            except Exception as e:
                logger.warning(f"Could not load opus: {e}")

    async def timeout_handler(self):
        """Method to handle timeout disconnection of the music player"""

        if self.guild.voice_client is None:
            return

        if len(self.guild.voice_client.channel.voice_states) == 1:
            await self.disconnect()
            return

        if VC_TIMEOUT == 0 or self.guild.voice_client.is_playing():
            await self.timer.restart()
            return

        await self.disconnect()
        await self.timer.stop()
        return

    ##################################
    ### Playback control functions ###
    ##################################

    async def process_request(self, itx: discord.Interaction, query: str):
        """Process user search and returns a list of search strings"""

        user_search = ddict(
            {
                "original": query,
                "url": extract_url(query),
                "playlist_type": music_utils.identify_playlist(query),
                "host": music_utils.identify_host(query),
            }
        )
        # logger.debug(f"Processing user search: {user_search}")
        logger.info(f"Processing user search: {user_search}")

        # Possibly process Youtube separately
        # if host == Sites.YouTube:
        #     await self._process_youtube_search(itx, query, url, playlist_type)

        try:
            # Process single keyword search
            if user_search.url is None:
                await self._add_to_queue(Search(query=user_search.original), itx.user, itx.channel)
                await itx.followup.send(
                    embed=discord.Embed(description=f"{Emojis.cd} Queued: `{query}`", color=EMBED_COLOR())
                )

            # Process single URL
            elif user_search.playlist_type == PlaylistTypes.Not_Playlist:
                search = self._get_song_info(user_search.url, user_search.host)
                await self._add_to_queue(search, itx.user, itx.channel)
                await itx.followup.send(
                    embed=discord.Embed(
                        description=f"{Emojis.cd} Queued: [{search.query}]({search.url})", color=EMBED_COLOR()
                    )
                )

            # Process Playlist
            else:
                playlist = self._get_playlist(user_search.url, user_search.playlist_type)
                if playlist is None:
                    raise CustomException("Could not find playlist.")

                await itx.followup.send(
                    embed=discord.Embed(
                        description=f"{Emojis.cd} Queued {playlist.total} items from playlist **{playlist.name}**",
                        color=EMBED_COLOR(),
                    )
                )

                # Queue and play first song immediately
                await asyncio.wait(
                    [asyncio.create_task(self._add_to_queue(playlist.items[0], itx.user, itx.channel))],
                    return_when=asyncio.ALL_COMPLETED,
                )
                if self.current_song is None:
                    self._next_song(itx.channel)
                    await asyncio.sleep(1)

                # Queue the rest of the songs
                for song in playlist.items[1:]:
                    try:
                        await self._add_to_queue(song, itx.user, itx.channel)
                    except CustomException as e:
                        logger.warning(e)
                        await send_embed(
                            channel=itx.channel, title=ErrorMessages.SEARCH_ERROR, description=f"```{e}```"
                        )
                        continue
        except CustomException as e:
            logger.warning(e)
            await send_embed(channel=itx.channel, title=ErrorMessages.SEARCH_ERROR, description=f"```{e}```")
        except Exception as e:
            logger.warning(f"Could not process search: {e}")
            await itx.followup.send(
                embed=discord.Embed(title=ErrorMessages.SEARCH_ERROR, description=f"```{e}```", color=EMBED_COLOR())
            )
            # raise Exception("Error processing search.").with_traceback(e.__traceback__)
            return False

        return

    def _get_song_info(self, url, host) -> Search:
        """Returns search for single track"""

        match host:
            case Sites.Spotify:
                logger.info(f"Processing Spotify track: {url}")
                search = music_utils.parse_spotify_track(self.sp, url)
            case Sites.YouTube:
                logger.info(f"Processing Youtube track: {url}")
                pass
            case Sites.Bandcamp:
                pass
            case _:  # Twitter, Soundcloud, etc.
                logger.info(f"Processing generic track: {url}")
                pass
        return search

    def _get_playlist(self, url, playlist_type) -> Playlist:
        """Returns object containing playlist info"""

        match playlist_type:
            case PlaylistTypes.Spotify_Playlist:
                logger.info(f"Processing Spotify playlist: {url}")
                playlist = music_utils.parse_spotify_playlist(self.sp, url)
                playlist = Playlist(name=playlist.name, total=playlist.total, items=playlist.items)
            case PlaylistTypes.YouTube_Playlist | PlaylistTypes.BandCamp_Playlist:
                logger.info(f"Processing Youtube playlist: {url}")
                # playlist_title, items = music_utils.parse_youtube_playlist(url)
                # with YoutubeDL({"ignoreerrors": True, "quiet": True}) as ydl:
                with YoutubeDL({"quiet": True}) as ydl:
                    r = ydl.extract_info(url, download=False)

                playlist = Playlist(
                    name=r["title"],
                    total=r["playlist_count"],
                    items=[
                        ddict(
                            {
                                "search": item["title"],
                                "url": item["original_url"],
                            }
                        )
                        for item in r["entries"]
                    ],
                )
                print(playlist.items)
            case _:  # Twitter, Soundcloud, etc.
                logger.warning(f"Could not process playlist: {url}")
                playlist = None

        return playlist

    async def _get_song_info_async(self, url, host):
        """Returns search string for single track"""
        return
        match host:
            case Sites.Spotify:  # is async spotify worth it?
                search_str = music_utils.parse_spotify_track(self.sp, url)
            case Sites.YouTube:
                pass  # try manual async version
            case Sites.Bandcamp:
                pass
            case _:  # Twitter, Soundcloud, etc.
                pass
        return search_str

    async def _get_playlist_async(self, url, playlist_type) -> Playlist:
        """Returns object containing playlist info"""
        return
        match playlist_type:
            case PlaylistTypes.Spotify_Playlist:
                logger.info(f"Processing Spotify playlist: {url}")
                playlist = music_utils.parse_spotify_playlist(self.sp, url)
                playlist = Playlist(name=playlist.title, total=playlist.total, items=playlist.tracks)
            case PlaylistTypes.YouTube_Playlist | PlaylistTypes.BandCamp_Playlist:
                logger.info(f"Processing Youtube playlist: {url}")
                # playlist_title, items = music_utils.parse_youtube_playlist(url)
                # with YoutubeDL({"ignoreerrors": True, "quiet": True}) as ydl:
                with YoutubeDL({"quiet": True}) as ydl:
                    r = ydl.extract_info(url, download=False)
                print(r.keys())
                playlist = Playlist(
                    name=r["title"],
                    total=r["playlist_count"],
                    # items = r['entries'],)
                    items=[
                        ddict(
                            {
                                "search": item["title"],
                                "url": item["original_url"],
                            }
                        )
                        for item in r["entries"]
                    ],
                )
                print(playlist.items)
            case _:  # Twitter, Soundcloud, etc.
                logger.warning(f"Could not process playlist: {url}")
                playlist = None

        return playlist

    async def _add_to_queue(self, search: Search, requested_by, channel=None):
        """Add list of searches to player queue"""

        yt_search = YouTubeSearchResults(title=None, url=None)

        # Get youtube URL
        if not search.url or "youtu" not in search.url:
            try:
                yt_search = music_utils.search_youtube(search.query)
            except Exception as e:
                raise CustomException(f"Could not find youtube url for {search.query}: {e}.")

        # Get song info from youtube URL
        data = music_utils.get_yt_metadata(yt_search.url)
        if data is None:
            raise CustomException(f"Could not get metadata for {search.url}.")

        song = Song(
            base_url=yt_search.url,
            original_url=search.url,
            requested_by=requested_by,
            channel_name=data["channel_name"],
            title=yt_search.title,
            duration=data["duration"],
            webpage_url=data["url"],
            thumbnail=data["thumbnails"]
            # thumbnail = data['thumbnails'][-1]['url'] if data['thumbnails'] is not None else None
        )

        self.queue.add(song)
        if self.current_song is None:
            self._next_song(channel)
        return

    async def _add_list_to_queue(
        self,
        items: list,
        requested_by,
    ):
        """Add list of searches to player queue"""
        return
        async for item in items:
            # Get youtube URL
            if "youtu" in item.url:
                yt_url = item.url
            else:
                try:
                    yt_url = music_utils.search_youtube(item.search)
                except Exception as e:
                    logger.warning(f"Could not find youtube url for {item.search}: {e}")
                    # yield CustomException(f"Could not find youtube url for {item.search}.")
                    continue

            # Get song info from youtube URL
            info = music_utils.get_yt_metadata(yt_url)
            if info is None:
                # raise Exception(f"Could not get metadata for {yt_url}.")
                yield CustomException(f"Could not get metadata for {yt_url}.")
                continue

            song = Song(
                base_url=yt_url,
                requested_by=requested_by,
                # base_url = info['url'],
                uploader=info["uploader"],
                title=info["title"],
                duration=info["duration"],
                webpage_url=info["webpage_url"],
                thumbnail=info["thumbnails"][-1]["url"] if info["thumbnails"] is not None else None,
            )
            self.queue.add(song)

        return

    def _next_song(self, channel):
        """Invoked after a song is finished. Plays the next song if there is one."""
        next_song = self.queue.next(self.current_song)
        self.current_song = None
        if next_song is None:
            coro = send_embed(
                channel=channel,
                description=InfoMessages.QUEUE_EMPTY,
            )
            self.bot.loop.create_task(coro)
        try:
            coro = self._play_song(channel, next_song)
            self.bot.loop.create_task(coro)
        except Exception as e:
            logger.error(f"Error: Couldn't play the next song:\n{e}")
        return

    async def _play_song(self, channel: discord.channel, song: Song):
        """Plays a song object"""

        if not self.queue.loop:  # let timer run through if looping
            # await self.timer.restart()
            self.timer.stop()
            self.timer = Timer(self.timeout_handler)
            logger.debug(f"Timer restarted")
        # song = song
        # logger.info(f"Next song: {song}")

        try:
            with YoutubeDL(YTDL_OPTIONS) as ydl:
                r = ydl.extract_info(song.base_url, download=False)
        except Exception:  # get actual exception later
            await asyncio.sleep(1)
            downloader = YoutubeDL({"title": True, "cookiefile": COOKIE_PATH})
            r = downloader.extract_info(song, download=False)

        song.base_url = r.get("url")
        self.current_song = song

        logger.info(f"Playing song: {song.title} ({song.duration} seconds) requested by {song.requested_by}")
        ffmpeg_options = {"options": "-vn"}
        self.guild.voice_client.play(
            discord.FFmpegPCMAudio(
                source=song.base_url,
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                **ffmpeg_options,
            ),
            after=lambda x: self._next_song(channel),
        )
        await channel.send(embed=song.now_playing_embed())

        # Download next X songs in background
        # for song in list(self.queue.playque)[:MAX_SONG_PRELOAD]:
        #     await asyncio.ensure_future(self.preload(song))
        return

    async def stop_player(self):
        """Stops the player and removes all songs from the queue"""
        if self.guild.voice_client is None or (
            not self.guild.voice_client.is_paused() and not self.guild.voice_client.is_playing()
        ):
            return

        self.queue.loop = False
        self.queue.next(self.current_song)
        self.clear_queue()
        self.guild.voice_client.stop()
        return

    def clear_queue(self):
        self.queue.playque.clear()
        return

    ##########################
    ### Connection Methods ###
    ##########################

    async def get_user_vc(self, itx: discord.Interaction) -> bool:
        """Return user's curernt VC, or None if user is not connected"""
        try:
            return itx.user.voice.channel
        except AttributeError:
            return None

    async def get_bot_vc(self, bot: discord.Client, itx: discord.Interaction):
        """Return bot's current VC, or None if bot is not connected"""
        try:
            bot_vc = discord.utils.get(bot.voice_clients, guild=itx.guild)
            return bot_vc.channel
        except AttributeError:
            return None

    async def get_bot_vc_alt(self, bot: discord.Client, itx: discord.Interaction):
        guild = bot.get_guild(itx.guild_id)
        try:
            voice_channel = guild.voice_client.channel
            return voice_channel
        except AttributeError:
            return None

    async def connect(self, itx: discord.Interaction, vc: discord.VoiceChannel):
        """Connect the bot to a VC"""
        try:
            await vc.connect(reconnect=True, timeout=None, self_deaf=True, self_mute=False)
            logger.info(f"Connected successfully: {vc.name}")
        except Exception as e:
            await itx.followup.send(f"ERROR: Could not connect to VC - {e}")
            raise e
        return

    async def disconnect(self):
        """Disconnect bot from VC"""
        await self.stop_player()
        if self.guild.voice_client is not None:
            await self.guild.voice_client.disconnect(force=True)
        return

    ####################
    ### Misc Helpers ###
    ####################

    # async def preload(self, song):
    #     import concurrent
    #     import yt_dlp

    #     if song.title != None:
    #         return

    #     def down(song):

    #         if song.host == Sites.Spotify:
    #             song.webpage_url = self.search_youtube(song.title)

    #         if song.webpage_url == None:
    #             return None

    #         downloader = yt_dlp.YoutubeDL(
    #             {'format': 'bestaudio', 'title': True, "cookiefile": COOKIE_PATH})
    #         r = downloader.extract_info(
    #             song.webpage_url, download=False)
    #         song.base_url = r.get('url')
    #         song.uploader = r.get('uploader')
    #         song.title = r.get('title')
    #         song.duration = r.get('duration')
    #         song.webpage_url = r.get('webpage_url')
    #         song.thumbnail = r.get('thumbnails')[0]['url']

    #     if song.host == Sites.Spotify:
    #         song.title = await music_utils.convert_spotify(song.webpage_url)

    #     loop = asyncio.get_event_loop()
    #     executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_SONG_PRELOAD)
    #     await asyncio.wait(fs={loop.run_in_executor(executor, down, song)}, return_when=asyncio.ALL_COMPLETED)
