import asyncio, aiohttp
import concurrent.futures

import discord
import spotipy
import yt_dlp

from music.music_config import *
from music.queue import Queue
from music.songinfo import Song
from music import music_utils
from music.music_utils import Sites, Origins, PlaylistTypes
from utils.log_utils import get_logger

# logger = get_logger(f"compass.{__name__}")
from loguru import logger


YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'title': True,
    "cookiefile": COOKIE_PATH,
    'default_search': 'auto',
    'extract_flat': 'in_playlist',
    'noplaylist': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'logger': get_logger("ytdl"),
    'quiet': True,
}


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
    """ 
    Controls the playback of audio and the sequential playing of the songs.

    Attributes:
        bot: The instance of the bot that will be playing the music.
        queue: A Queue object that stores the history and queue of songs.
        current_song: A Song object that stores details of the current song.
        guild: The guild in which the MusicPlayer operates.
    """

    def __init__(self, bot, guild):
        self.bot = bot
        self.queue = Queue()
        self.current_song = None
        self.guild = guild

        sett = music_utils.guild_settings[guild]
        self.timer = Timer(self.timeout_handler)
        self._volume = sett.get('default_volume')
        
        if ~ discord.opus.is_loaded():
            try: 
                discord.opus.load_opus('libopus.so.0')
                logger.debug("Opus successfully loaded")
            except Exception as e:
                logger.warning(f"Could not load opus: {e}")

    ### Properties ###
    
    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value):
        self._volume = value
        try:
            self.guild.voice_client.source.volume = float(value) / 100.0
        except Exception as e:
            pass

    ##################################
    ### Playback control functions ###
    ##################################
        
    
    async def process_search(self, ctx, search):
        """Process user search and returns a list of search strings"""

        searches = []
        
        host = music_utils.identify_host(search)
        playlist_type = music_utils.identify_playlist(search)

        # If it's a playlist, process it and return
        if playlist_type != PlaylistTypes.Not_Playlist:    
            await self.process_playlist(ctx, url=search, playlist_type=playlist_type)
            
            if self.current_song == None:
                await self.play_song(ctx, self.queue.playque[0])
                logger.info("Playing {}".format(search))

            song = Song(
                        origin=Origins.Playlist, 
                        host=Sites.Unknown,
                        requested_by=ctx.message.author
                    )
            return song

        # If it's a single song, process it and return
        if host == Sites.Unknown:
            if music_utils.extract_url(search) is not None:
                return
            searches.append(search)

        if host == Sites.SoundCloud:
            searches.append(search)
            
        if host == Sites.Spotify:
            try:
                sp_searches = music_utils.process_spotify_url(search)
            except spotipy.exceptions.SpotifyException:
                await ctx.send(f"Error processing Spotify URL")
                return
            searches = searches + sp_searches

        if host == Sites.YouTube:
            track = track.split("&list=")[0]

        await self.add_to_queue(searches, requested_by=ctx.message.author, host=host)

        if self.current_song == None:
              self._next_song(ctx)

        return
    
    async def add_to_queue(self, searches: list, requested_by, host):  
        """Add list of searches to player queue"""

        for search in searches:
            try:
                yt_url = self.search_youtube(search)
                # downloader = yt_dlp.YoutubeDL({'format': 'bestaudio', 'title': True, "cookiefile": COOKIE_PATH})
                downloader = yt_dlp.YoutubeDL(YTDL_OPTIONS)
                try:
                    r = downloader.extract_info(yt_url, download=False)
                except Exception as e:
                    if "ERROR: Sign in to confirm your age" in str(e):
                        return None
            except:
                downloader = yt_dlp.YoutubeDL({'title': True, "cookiefile": COOKIE_PATH})
                r = downloader.extract_info(search, download=False)

            thumbnail = r.get('thumbnails')[len(r.get('thumbnails')) - 1]['url'] if r.get('thumbnails') is not None else None

            song = Song(
                origin = Origins.Default,
                host = host,
                base_url = r.get('url'),
                requested_by = requested_by,
                uploader = r.get('uploader'),
                title = r.get('title'),
                duration = r.get('duration'),
                webpage_url = r.get('webpage_url'),
                thumbnail = thumbnail
            )
            self.queue.add(song)

        return

    async def process_playlist(self, ctx, url, playlist_type):

        if playlist_type == PlaylistTypes.YouTube_Playlist:

            if ("playlist?list=" in url):
                listid = url.split('=')[1]
            else:
                video = url.split('&')[0]
                await self.process_song(ctx, track=video)
                return

            with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
                r = ydl.extract_info(url, download=False)

                for entry in r['entries']:

                    link = "https://www.youtube.com/watch?v={}".format(
                        entry['id'])

                    song = Song(
                                origin = Origins.Playlist,
                                host = Sites.YouTube,
                                webpage_url=link,
                                requested_by=ctx.message.author
                            )

                    self.queue.add(song)

        if playlist_type == PlaylistTypes.Spotify_Playlist:
            links = await music_utils.get_spotify_playlist(url=url)
            for link in links:
                song = Song(
                            origin=Origins.Playlist,
                            host=Sites.Spotify,
                            requested_by=ctx.message.author,
                            webpage_url=link
                        )
                self.queue.add(song)

        if playlist_type == PlaylistTypes.BandCamp_Playlist:
            
            with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
                r = ydl.extract_info(url, download=False)

                for entry in r['entries']:

                    link = entry.get('url')

                    song = Song(
                                origin=Origins.Playlist,
                                host=Sites.Bandcamp,
                                requested_by=ctx.message.author,
                                webpage_url=link
                            )

                    self.queue.add(song)

        for song in list(self.queue.playque)[:MAX_SONG_PRELOAD]:
            await asyncio.ensure_future(self.preload(song))

    async def preload(self, song):

        if song.title != None:
            return

        def down(song):

            if song.host == Sites.Spotify:
                song.webpage_url = self.search_youtube(song.title)

            if song.webpage_url == None:
                return None

            downloader = yt_dlp.YoutubeDL(
                {'format': 'bestaudio', 'title': True, "cookiefile": COOKIE_PATH})
            r = downloader.extract_info(
                song.webpage_url, download=False)
            song.base_url = r.get('url')
            song.uploader = r.get('uploader')
            song.title = r.get('title')
            song.duration = r.get('duration')
            song.webpage_url = r.get('webpage_url')
            song.thumbnail = r.get('thumbnails')[0]['url']

        if song.host == Sites.Spotify:
            song.title = await music_utils.convert_spotify(song.webpage_url)

        loop = asyncio.get_event_loop()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_SONG_PRELOAD)
        await asyncio.wait(fs={loop.run_in_executor(executor, down, song)}, return_when=asyncio.ALL_COMPLETED)

    async def play_song(self, ctx, song):
        """Plays a song object"""

        if self.queue.loop != True: #let timer run through if looping
            # await self.timer.restart()
            self.timer.stop()
            self.timer = Timer(self.timeout_handler)

        if song.title == None:
            if song.host == Sites.Spotify:
                try:
                    search_str = await music_utils.convert_spotify(song.webpage_url)
                    conversion = self.search_youtube(search_str)
                    song.webpage_url = conversion
                except Exception as e:
                    logger.error(f"Error: couldn't convert Spotify link: \n{e}")

            try:
                downloader = yt_dlp.YoutubeDL({'format': 'bestaudio', 'title': True, "cookiefile": COOKIE_PATH})
                r = downloader.extract_info(song.webpage_url, download=False)
            except:
                await asyncio.wait(2)
                downloader = yt_dlp.YoutubeDL({'title': True, "cookiefile": COOKIE_PATH})
                r = downloader.extract_info(song, download=False)

            song.base_url = r.get('url')
            song.uploader = r.get('uploader')
            song.title = r.get('title')
            song.duration = r.get('duration')
            song.webpage_url = r.get('webpage_url')
            song.thumbnail = r.get('thumbnails')[0]['url']

        self.queue.add_name(song.title)
        self.current_song = song
        self.queue.playhistory.append(self.current_song)

        self.guild.voice_client.play(
            discord.FFmpegPCMAudio(
                source = song.base_url,
                before_options = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
            ), 
            after = lambda e: self._next_song(ctx)
        )

        await ctx.send(embed=song.format_output(SONGINFO_NOW_PLAYING))

        self.guild.voice_client.source = discord.PCMVolumeTransformer(self.guild.voice_client.source)
        self.guild.voice_client.source.volume = float(self.volume) / 100.0

        self.queue.playque.popleft()

        #loop = asyncio.get_event_loop()
        for song in list(self.queue.playque)[:MAX_SONG_PRELOAD]:
            await asyncio.ensure_future(self.preload(song))

    def _next_song(self, ctx):
        """Invoked after a song is finished. Plays the next song if there is one."""

        next_song = self.queue.next(self.current_song)

        self.current_song = None
        try:
            coro = self.play_song(ctx, next_song)
        except Exception as e:
            logger.error(f"Error: Couldn't play the next song:\n{e}")
        
        self.bot.loop.create_task(coro)

    async def prev_song(ctx, self):
        """Loads the last song from the history into the queue and starts it"""

        self.timer.stop()
        self.timer = Timer(self.timeout_handler)

        if len(self.queue.playhistory) == 0:
            return

        prev_song = self.queue.prev(self.current_song)

        if not self.guild.voice_client.is_playing() and not self.guild.voice_client.is_paused():

            if prev_song == "Dummy":
                self.queue.next(self.current_song)
                return None
            await self.play_song(ctx, prev_song)
        else:
            self.guild.voice_client.stop()

    async def stop_player(self):
        """Stops the player and removes all songs from the queue"""
        if self.guild.voice_client is None or (
                not self.guild.voice_client.is_paused() and not self.guild.voice_client.is_playing()):
            return

        self.queue.loop = False
        self.queue.next(self.current_song)
        self.clear_queue()
        self.guild.voice_client.stop()
        return

    def clear_queue(self):
        self.queue.playque.clear()
        return
    
    def track_history(self):
        history_string = INFO_HISTORY_TITLE
        for trackname in self.queue.trackname_history:
            history_string += "\n" + trackname
        return history_string
    
    ########################
    ### Helper functions ###
    ########################
    
    def get_yt_metadata(self):
        return

    def search_youtube(self, search_str):
        """Searches youtube for the video title and returns the first results video link"""

        # if title is already a link
        if music_utils.extract_url(search_str) is not None:
            return search_str

        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            r = ydl.extract_info(search_str, download=False)

        if r == None:
            return None

        videocode = r['entries'][0]['id']

        return "https://www.youtube.com/watch?v={}".format(videocode)

    ##########################
    ### Connection Methods ###
    ##########################

    async def connect_to_vc(self, channel):
        """Connect the bot to a VC"""
        await channel.connect(reconnect=True, timeout=None)

    async def check_user_vc(self, itx) -> bool:
        """Check if a user is in a VC"""
        try:
            user_vc = itx.user.voice
            return user_vc
        except AttributeError:
            return False
    
    async def timeout_handler(self):

        sett = music_utils.guild_settings[self.guild]

        if len(self.guild.voice_client.channel.voice_states) == 1:
            await self.udisconnect()
            return

        if (sett.get('vc_timeout') == 0 or 
            self.guild.voice_client.is_playing()):
            await self.timer.restart()
            return

        await self.udisconnect()
        await self.timer.stop()
        return

    async def uconnect(self, ctx):
        """ ???????? """
        if not await self.check_user_vc(ctx):
            return False

        if self.guild.voice_client is None:
            await ctx.author.voice.channel.connect(reconnect=True, timeout=None)
        else:
            await ctx.send("Already connected to a voice channel.")

    async def udisconnect(self):
        """ ???????? """
        await self.stop_player()
        if self.guild.voice_client is not None:
            await self.guild.voice_client.disconnect(force=True)
        return
        

