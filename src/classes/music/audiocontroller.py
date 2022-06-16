import os, discord
import yt_dlp, asyncio, aiohttp
import concurrent.futures

import utils.music_config as config
import utils.music_utils as utils

from classes.music.queue import Queue
from classes.music.songinfo import Song
from utils.helper import *

logger = get_logger(__name__)

ffmpeg = f"{os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))}/ffmpeg"
ytdl_options = {
            'format': 'bestaudio/best',
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
            "cookiefile": config.COOKIE_PATH
        }

class AudioController(object):
    """ 
    Controls the playback of audio and the sequential playing of the songs.

    Attributes:
        bot: The instance of the bot that will be playing the music.
        queue: A Queue object that stores the history and queue of songs.
        current_song: A Song object that stores details of the current song.
        guild: The guild in which the Audiocontroller operates.
    """

    def __init__(self, bot, guild):
        self.bot = bot
        self.queue = Queue()
        self.current_song = None
        self.guild = guild

        sett = utils.guild_settings[guild]
        self.timer = utils.Timer(self.timeout_handler)
        self._volume = sett.get('default_volume')
        
        self.session = aiohttp.ClientSession()
        
        if ~ discord.opus.is_loaded():
            try: 
                discord.opus.load_opus('libopus.so.0')
                logger.info("Opus successfully loaded")
            except Exception as e:
                logger.info("Something went wrong: {}".format(e))

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

    ### Playback control functions ###

    async def play_song(self, ctx, song):
        """Plays a song object"""

        if self.queue.loop != True: #let timer run thouh if looping
            self.timer.cancel()
            self.timer = utils.Timer(self.timeout_handler)

        if song.info.title == None:
            if song.host == utils.Sites.Spotify:
                conversion = self.search_youtube(await utils.convert_spotify(self.session, song.info.webpage_url))
                song.info.webpage_url = conversion

            try:
                downloader = yt_dlp.YoutubeDL({'format': 'bestaudio', 'title': True, "cookiefile": config.COOKIE_PATH})
                r = downloader.extract_info(song.info.webpage_url, download=False)
            except:
                asyncio.wait(2)
                downloader = yt_dlp.YoutubeDL({'title': True, "cookiefile": config.COOKIE_PATH})
                r = downloader.extract_info(song, download=False)

            song.base_url = r.get('url')
            song.info.uploader = r.get('uploader')
            song.info.title = r.get('title')
            song.info.duration = r.get('duration')
            song.info.webpage_url = r.get('webpage_url')
            song.info.thumbnail = r.get('thumbnails')[0]['url']

        self.queue.add_name(song.info.title)
        self.current_song = song

        self.queue.playhistory.append(self.current_song)

        self.guild.voice_client.play(
            discord.FFmpegPCMAudio(
                executable = ffmpeg,
                source = song.base_url,
                before_options = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
                ), 
            after=lambda e: self.next_song(ctx, e)
        )

        #await ctx.send(embed=song.info.format_output(config.SONGINFO_NOW_PLAYING))

        self.guild.voice_client.source = discord.PCMVolumeTransformer(self.guild.voice_client.source)
        self.guild.voice_client.source.volume = float(self.volume) / 100.0

        self.queue.playque.popleft()

        #loop = asyncio.get_event_loop()
        for song in list(self.queue.playque)[:config.MAX_SONG_PRELOAD]:
            await asyncio.ensure_future(self.preload(song))

    async def process_song(self, ctx, track):
        """Adds the track/playlist to the queue instance and plays it, if it is the first song"""

        # Get the host from url, and check if playlist
        host = utils.identify_host(track)
        playlist_type = utils.identify_playlist(track)

        # If input is a playlist
        if playlist_type != utils.Playlist_Types.Unknown:

            await self.process_playlist(ctx, url=track, playlist_type=playlist_type)

            if self.current_song == None:
                await self.play_song(ctx, self.queue.playque[0])
                logger.info("Playing {}".format(track))

            song = Song(
                        origin=utils.Origins.Playlist, 
                        host=utils.Sites.Unknown,
                        requested_by=ctx.message.author
                    )
            return song


        if host == utils.Sites.Unknown:
            if utils.get_url(track) is not None:
                return None

            track = self.search_youtube(track)

        if host == utils.Sites.Spotify:
            title = await utils.convert_spotify(self.session, track)
            track = self.search_youtube(title)

        if host == utils.Sites.YouTube:
            track = track.split("&list=")[0]

        try:
            downloader = yt_dlp.YoutubeDL({'format': 'bestaudio', 'title': True, "cookiefile": config.COOKIE_PATH})
            try:
                r = downloader.extract_info(track, download=False)
            except Exception as e:
                if "ERROR: Sign in to confirm your age" in str(e):
                    return None
        except:
            downloader = yt_dlp.YoutubeDL({'title': True, "cookiefile": config.COOKIE_PATH})
            r = downloader.extract_info(track, download=False)

        thumbnail = r.get('thumbnails')[len(r.get('thumbnails')) - 1]['url'] if r.get('thumbnails') is not None else None

        song = Song(
            origin = utils.Origins.Default,
            host = host,
            base_url=r.get('url'),
            requested_by=ctx.message.author,
            uploader=r.get('uploader'),
            title=r.get('title'),
            duration=r.get('duration'),
            webpage_url=r.get('webpage_url'),
            thumbnail=thumbnail
        )

        self.queue.add(song)
        
        if self.current_song == None:
            logger.info("Playing {}".format(track))
            await self.play_song(ctx, song)

        return song

    async def process_playlist(self, ctx, url, playlist_type):

        if playlist_type == utils.Playlist_Types.YouTube_Playlist:

            if ("playlist?list=" in url):
                listid = url.split('=')[1]
            else:
                video = url.split('&')[0]
                await self.process_song(ctx, track=video)
                return

            with yt_dlp.YoutubeDL(ytdl_options) as ydl:
                r = ydl.extract_info(url, download=False)

                for entry in r['entries']:

                    link = "https://www.youtube.com/watch?v={}".format(
                        entry['id'])

                    song = Song(
                                origin = utils.Origins.Playlist,
                                host = utils.Sites.YouTube,
                                webpage_url=link,
                                requested_by=ctx.message.author
                            )

                    self.queue.add(song)

        if playlist_type == utils.Playlist_Types.Spotify_Playlist:
            links = await utils.get_spotify_playlist(session=self.session, url=url)
            for link in links:
                song = Song(
                            origin=utils.Origins.Playlist,
                            host=utils.Sites.Spotify,
                            requested_by=ctx.message.author,
                            webpage_url=link
                        )
                self.queue.add(song)

        if playlist_type == utils.Playlist_Types.BandCamp_Playlist:
            
            with yt_dlp.YoutubeDL(ytdl_options) as ydl:
                r = ydl.extract_info(url, download=False)

                for entry in r['entries']:

                    link = entry.get('url')

                    song = Song(
                                origin=utils.Origins.Playlist,
                                host=utils.Sites.Bandcamp,
                                requested_by=ctx.message.author,
                                webpage_url=link
                            )

                    self.queue.add(song)

        for song in list(self.queue.playque)[:config.MAX_SONG_PRELOAD]:
            await asyncio.ensure_future(self.preload(song))

    async def preload(self, song):

        if song.info.title != None:
            return

        def down(song):

            if song.host == utils.Sites.Spotify:
                song.info.webpage_url = self.search_youtube(song.info.title)

            if song.info.webpage_url == None:
                return None

            downloader = yt_dlp.YoutubeDL(
                {'format': 'bestaudio', 'title': True, "cookiefile": config.COOKIE_PATH})
            r = downloader.extract_info(
                song.info.webpage_url, download=False)
            song.base_url = r.get('url')
            song.info.uploader = r.get('uploader')
            song.info.title = r.get('title')
            song.info.duration = r.get('duration')
            song.info.webpage_url = r.get('webpage_url')
            song.info.thumbnail = r.get('thumbnails')[0]['url']

        if song.host == utils.Sites.Spotify:
            song.info.title = await utils.convert_spotify(self.session, song.info.webpage_url)

        loop = asyncio.get_event_loop()
        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=config.MAX_SONG_PRELOAD)
        await asyncio.wait(fs={loop.run_in_executor(executor, down, song)}, return_when=asyncio.ALL_COMPLETED)

    def next_song(self, ctx, error):
        """Invoked after a song is finished. Plays the next song if there is one."""

        #if error:
        #    await ctx.send(discord.Embed(description=f"{error}"))

        next_song = self.queue.next(self.current_song)

        self.current_song = None

        coro = self.play_song(ctx, next_song)
        
        self.bot.loop.create_task(coro)

    async def prev_song(ctx, self):
        """Loads the last song from the history into the queue and starts it"""

        self.timer.cancel()
        self.timer = utils.Timer(self.timeout_handler)

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

    def clear_queue(self):
        self.queue.playque.clear()
    
    ### Helper functions ###

    def search_youtube(self, title):
        """Searches youtube for the video title and returns the first results video link"""

        # if title is already a link
        if utils.get_url(title) is not None:
            return title

        with yt_dlp.YoutubeDL(ytdl_options) as ydl:
            r = ydl.extract_info(title, download=False)

        if r == None:
            return None

        videocode = r['entries'][0]['id']

        return "https://www.youtube.com/watch?v={}".format(videocode)
        
    async def register_voice_channel(self, channel):
        await channel.connect(reconnect=True, timeout=None)

    def track_history(self):
        history_string = config.INFO_HISTORY_TITLE
        for trackname in self.queue.trackname_history:
            history_string += "\n" + trackname
        return history_string

    async def timeout_handler(self):

        if len(self.guild.voice_client.channel.voice_states) == 1:
            await self.udisconnect()
            return

        sett = utils.guild_settings[self.guild]

        if sett.get('vc_timeout') == False:
            self.timer = utils.Timer(self.timeout_handler)  # restart timer
            return

        if self.guild.voice_client.is_playing():
            self.timer = utils.Timer(self.timeout_handler)  # restart timer
            return

        self.timer = utils.Timer(self.timeout_handler)
        await self.udisconnect()

    async def uconnect(self, ctx):

        if not ctx.author.voice:
            await ctx.send(config.NO_GUILD_MESSAGE)
            return False

        if self.guild.voice_client == None:
            await self.register_voice_channel(ctx.author.voice.channel)
        else:
            await ctx.send(config.ALREADY_CONNECTED_MESSAGE)

    async def udisconnect(self):
        await self.stop_player()
        await self.guild.voice_client.disconnect(force=True)
