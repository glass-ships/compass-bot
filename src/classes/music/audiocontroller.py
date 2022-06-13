import os, discord
import yt_dlp, asyncio
import concurrent.futures
#from redis import AuthenticationError

import utils.music_config as config
import utils.music_utils as utils

from classes.music.playlist import Playlist
from classes.music.songinfo import Song
from utils.helper import *

logger = get_logger(__name__)
ffmpeg = f"{os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))}/ffmpeg"

class AudioController(object):
    """ 
    Controls the playback of audio and the sequential playing of the songs.

    Attributes:
        bot: The instance of the bot that will be playing the music.
        playlist: A Playlist object that stores the history and queue of songs.
        current_song: A Song object that stores details of the current song.
        guild: The guild in which the Audiocontroller operates.
    """

    def __init__(self, bot, guild):
        self.bot = bot
        self.playlist = Playlist()
        self.current_song = None
        self.guild = guild

        sett = utils.guild_to_settings[guild]
        self._volume = sett.get('default_volume')

        self.timer = utils.Timer(self.timeout_handler)

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

    async def register_voice_channel(self, channel):
        await channel.connect(reconnect=True, timeout=None)

    def track_history(self):
        history_string = config.INFO_HISTORY_TITLE
        for trackname in self.playlist.trackname_history:
            history_string += "\n" + trackname
        return history_string

    def next_song(self, ctx, session, error):
        """Invoked after a song is finished. Plays the next song if there is one."""

        next_song = self.playlist.next(self.current_song)

        self.current_song = None

        coro = self.play_song(ctx, session, next_song)
        self.bot.loop.create_task(coro)

    async def play_song(self, ctx, session, song):
        """Plays a song object"""

        if self.playlist.loop != True: #let timer run thouh if looping
            self.timer.cancel()
            self.timer = utils.Timer(self.timeout_handler)

        if song.info.title == None:
            if song.host == utils.Sites.Spotify:
                conversion = self.search_youtube(await utils.convert_spotify(session, song.info.webpage_url))
                song.info.webpage_url = conversion

            try:
                downloader = yt_dlp.YoutubeDL(
                    {'format': 'bestaudio', 'title': True, "cookiefile": config.COOKIE_PATH})
                r = downloader.extract_info(
                    song.info.webpage_url, download=False)
            except:
                asyncio.wait(1)
                downloader = yt_dlp.YoutubeDL(
                    {'title': True, "cookiefile": config.COOKIE_PATH})
                r = downloader.extract_info(
                    song, download=False)


            song.base_url = r.get('url')
            song.info.uploader = r.get('uploader')
            song.info.title = r.get('title')
            song.info.duration = r.get('duration')
            song.info.webpage_url = r.get('webpage_url')
            song.info.thumbnail = r.get('thumbnails')[0]['url']

        self.playlist.add_name(song.info.title)
        self.current_song = song

        self.playlist.playhistory.append(self.current_song)

        if ~ discord.opus.is_loaded():
            try: 
                discord.opus.load_opus('libopus.so.0')
                logger.info("Opus successfully loaded")
            except Exception as e:
                logger.info("Something went wrong: {}".format(e))

        self.guild.voice_client.play(
            discord.FFmpegPCMAudio(
                executable = ffmpeg,
                source = song.base_url,
                before_options = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
                ), 
            after=lambda e: self.next_song(ctx, session, e)
        )

        #await ctx.send(embed=song.info.format_output(config.SONGINFO_NOW_PLAYING))

        self.guild.voice_client.source = discord.PCMVolumeTransformer(self.guild.voice_client.source)
        self.guild.voice_client.source.volume = float(self.volume) / 100.0

        self.playlist.playque.popleft()

        for song in list(self.playlist.playque)[:config.MAX_SONG_PRELOAD]:
            asyncio.ensure_future(self.preload(session, song))

    async def process_song(self, ctx, session, track):
        """Adds the track to the playlist instance and plays it, if it is the first song"""

        host = utils.identify_url(track)
        playlist_type = utils.identify_playlist(track)

        if playlist_type != utils.Playlist_Types.Unknown:

            await self.process_playlist(ctx, session=session, url=track, playlist_type=playlist_type)

            if self.current_song == None:
                await self.play_song(ctx, session, self.playlist.playque[0])
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
            title = await utils.convert_spotify(session, track)
            track = self.search_youtube(title)

        if host == utils.Sites.YouTube:
            track = track.split("&list=")[0]

        try:
            downloader = yt_dlp.YoutubeDL({'format': 'bestaudio', 'title': True, "cookiefile": config.COOKIE_PATH})
            try:
                r = downloader.extract_info(track, download=False)
                print(r)
            except Exception as e:
                if "ERROR: Sign in to confirm your age" in str(e):
                    return None
        except:
            downloader = yt_dlp.YoutubeDL({'title': True, "cookiefile": config.COOKIE_PATH})
            r = downloader.extract_info(track, download=False)

        if r.get('thumbnails') is not None:
            thumbnail = r.get('thumbnails')[len(r.get('thumbnails')) - 1]['url']
            print("Thumbnail: ", thumbnail)
        else:
            thumbnail = None

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

        self.playlist.add(song)
        
        if self.current_song == None:
            logger.info("Playing {}".format(track))
            await self.play_song(ctx, session, song)

        return song

    async def process_playlist(self, ctx, session, url, playlist_type):

        if playlist_type == utils.Playlist_Types.YouTube_Playlist:

            if ("playlist?list=" in url):
                listid = url.split('=')[1]
            else:
                video = url.split('&')[0]
                await self.process_song(ctx, session=session, track=video)
                return

            options = {
                'format': 'bestaudio/best',
                'extract_flat': True,
                "cookiefile": config.COOKIE_PATH
            }

            with yt_dlp.YoutubeDL(options) as ydl:
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

                    self.playlist.add(song)

        if playlist_type == utils.Playlist_Types.Spotify_Playlist:
            links = await utils.get_spotify_playlist(session=session, url=url)
            for link in links:
                song = Song(
                            origin=utils.Origins.Playlist,
                            host=utils.Sites.Spotify,
                            requested_by=ctx.message.author,
                            webpage_url=link
                        )
                self.playlist.add(song)

        if playlist_type == utils.Playlist_Types.BandCamp_Playlist:
            options = {
                'format': 'bestaudio/best',
                'extract_flat': True
            }
            with yt_dlp.YoutubeDL(options) as ydl:
                r = ydl.extract_info(url, download=False)

                for entry in r['entries']:

                    link = entry.get('url')

                    song = Song(
                                origin=utils.Origins.Playlist,
                                host=utils.Sites.Bandcamp,
                                requested_by=ctx.message.author,
                                webpage_url=link
                            )

                    self.playlist.add(song)

        for song in list(self.playlist.playque)[:config.MAX_SONG_PRELOAD]:
            asyncio.ensure_future(self.preload(session, song))

    async def preload(self, session, song):

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
            song.info.title = await utils.convert_spotify(session, song.info.webpage_url)

        loop = asyncio.get_event_loop()
        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=config.MAX_SONG_PRELOAD)
        await asyncio.wait(fs={loop.run_in_executor(executor, down, song)}, return_when=asyncio.ALL_COMPLETED)

    def search_youtube(self, title):
        """Searches youtube for the video title and returns the first results video link"""

        # if title is already a link
        if utils.get_url(title) is not None:
            return title

        options = {
            'format': 'bestaudio/best',
            'default_search': 'auto',
            'noplaylist': True,
            "cookiefile": config.COOKIE_PATH
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            r = ydl.extract_info(title, download=False)

        if r == None:
            return None

        videocode = r['entries'][0]['id']

        return "https://www.youtube.com/watch?v={}".format(videocode)

    async def stop_player(self):
        """Stops the player and removes all songs from the queue"""
        if self.guild.voice_client is None or (
                not self.guild.voice_client.is_paused() and not self.guild.voice_client.is_playing()):
            return

        self.playlist.loop = False
        self.playlist.next(self.current_song)
        self.clear_queue()
        self.guild.voice_client.stop()

    async def prev_song(ctx, session, self):
        """Loads the last song from the history into the queue and starts it"""

        self.timer.cancel()
        self.timer = utils.Timer(self.timeout_handler)

        if len(self.playlist.playhistory) == 0:
            return

        prev_song = self.playlist.prev(self.current_song)

        if not self.guild.voice_client.is_playing() and not self.guild.voice_client.is_paused():

            if prev_song == "Dummy":
                self.playlist.next(self.current_song)
                return None
            await self.play_song(ctx, session, prev_song)
        else:
            self.guild.voice_client.stop()

    async def timeout_handler(self):

        if len(self.guild.voice_client.channel.voice_states) == 1:
            await self.udisconnect()
            return

        sett = utils.guild_to_settings[self.guild]

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

    def clear_queue(self):
        self.playlist.playque.clear()
