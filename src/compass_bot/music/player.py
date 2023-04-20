import asyncio 
# import aiohttp

import discord
import spotipy
from yt_dlp import YoutubeDL
from loguru import logger

from compass_bot.utils.bot_config import EMBED_COLOR, Emojis
from compass_bot.utils.utils import send_embed
from compass_bot.music import music_utils
from compass_bot.music.dataclasses import Playlist, PlaylistTypes, Sites, Song
from compass_bot.music.music_config import ErrorMessages, COOKIE_PATH, VC_TIMEOUT, SPOTIFY_ID, SPOTIFY_SECRET, YTDL_OPTIONS
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
    """ Controls the playback of audio and the sequential playing of the songs.

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

        if ~ discord.opus.is_loaded():
            try: 
                discord.opus.load_opus('libopus.so.0')
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
        
        if (VC_TIMEOUT == 0 or
            self.guild.voice_client.is_playing()):
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
        
        url = music_utils.extract_url(query)
        playlist_type = music_utils.identify_playlist(url)
        host = music_utils.identify_host(url)
        
        logger.debug(f"Processing search: {url or query}")
        try:
            if url is None: 
                await self._add_to_queue([query], itx.user)
                await itx.followup.send(embed=discord.Embed(
                    title=Emojis.cd,
                    description=f"Queued: `{query}`.", 
                    color=EMBED_COLOR()
                ))

            # If single track, get Song info and add to queue
            elif playlist_type == PlaylistTypes.Not_Playlist:
                search_str = await self._get_song_info(url, host)
                await self._add_to_queue([search_str], itx.user)
                await itx.followup.send(embed=discord.Embed(
                    description=f"{Emojis.cd} Queued: `{search_str}.`",
                    color=EMBED_COLOR()
                ))
                
            # If Playlist, get Playlist info and add to queue
            else:
                playlist_info = await self._get_playlist_info(url, playlist_type)
                if playlist_info is not None:
                    await self._add_to_queue(playlist_info['tracks'], itx.user)
                    await itx.followup.send(embed=discord.Embed(
                        description=f"Queued {playlist_info['num_tracks']} from playlist **{playlist_info['title']}**"),
                        color=EMBED_COLOR()
                    )
        except Exception as e:
            logger.warning(f"Could not process search: {e}")
            await itx.followup.send(embed=discord.Embed(
                title=ErrorMessages.SEARCH_ERROR, 
                description=f"Could not process search: {e}",
                color=EMBED_COLOR()) 
            )
            return False

        if self.current_song == None:
            self._next_song(itx.channel)
        
        return

    async def _get_song_info(self, url, host):
        """Returns search string for single track"""

        match host:
            case Sites.Spotify:
                search_str = music_utils.parse_spotify_track(self.sp, url)
            case Sites.YouTube:
                pass
            case Sites.Bandcamp:
                pass
            case _: # Twitter, Soundcloud, etc.
                pass
        return search_str
            
    async def _get_playlist_info(self, url, playlist_type) -> Playlist:
        """Returns object containing playlist info"""

        match playlist_type:
            case PlaylistTypes.Spotify_Playlist:
                playlist_title, items = music_utils.parse_spotify_playlist(self.sp, url)
                playlist_info = Playlist(
                    name = playlist_title,
                    total = len(items),
                    items = items
                )
            case PlaylistTypes.YouTube_Playlist | PlaylistTypes.BandCamp_Playlist:
                with YoutubeDL(YTDL_OPTIONS) as ydl:
                    r = ydl.extract_info(f"ytsearch{url}", download=False)['entries'][0]
                playlist_info = Playlist(
                    name = r['title'],
                    total = r['playlist_count'],
                    items = r['entries']
                )
            case _: # Twitter, Soundcloud, etc.
                playlist_info = None
                
        return playlist_info

    async def _add_to_queue(
            self,  
            searches: list,
            requested_by,
        ):
        """Add list of searches to player queue"""
        
        for search in searches:
            # Convert search string to YouTube URL
            try: 
                yt_url = music_utils.search_youtube(search)
            except Exception as e:
                logger.warning(f"Could not find youtube url for {search}: {e}")
                raise Exception(f"Could not find youtube url for {search}: {e}")


            try:
                # downloader = YoutubeDL({'format': 'bestaudio', 'title': True, "cookiefile": COOKIE_PATH})
                downloader = YoutubeDL(YTDL_OPTIONS)
                try:
                    r = downloader.extract_info(yt_url, download=False)
                except Exception as e:
                    if "ERROR: Sign in to confirm your age" in str(e):
                        return None
            except:
                downloader = YoutubeDL({'title': True, "cookiefile": COOKIE_PATH})
                r = downloader.extract_info(search, download=False)

            thumbnail = r.get('thumbnails')[len(r.get('thumbnails')) - 1]['url'] if r.get('thumbnails') is not None else None

            song = Song(
                # host = host,
                base_url = r.get('url'),
                requested_by = requested_by,
                uploader = r.get('uploader'),
                title = r.get('title'),
                duration = r.get('duration'),
                webpage_url = r.get('webpage_url'),
                thumbnail = thumbnail
            )
            self.queue.add(song)

        return song

    def _next_song(self, channel):
        """Invoked after a song is finished. Plays the next song if there is one."""
        
        next_song = self.queue.next(self.current_song)
        self.current_song = None
        if next_song is None:
            coro = send_embed(
                channel=channel,
                description=f"{Emojis.jar} Queue is empty.",
                )
            self.bot.loop.create_task(coro)
            return None
        
        try:
            coro = self._play_song(channel, next_song)
            self.bot.loop.create_task(coro)
        except Exception as e:
            logger.error(f"Error: Couldn't play the next song:\n{e}")
        

    async def _play_song(self, channel, song: Song):
        """Plays a song object"""

        if not self.queue.loop: # let timer run through if looping
            # await self.timer.restart()
            self.timer.stop()
            self.timer = Timer(self.timeout_handler)
            logger.info(f"Timer restarted")

        try:
            with YoutubeDL(YTDL_OPTIONS) as ydl:
                r = ydl.extract_info(song.webpage_url, download=False)
        except:
            asyncio.wait(2)
            downloader = YoutubeDL({'title': True, "cookiefile": COOKIE_PATH})
            r = downloader.extract_info(song, download=False)
        
        song.base_url = r.get('url')
        song.uploader = r.get('uploader')
        song.title = r.get('title')
        song.duration = r.get('duration')
        song.webpage_url = r.get('webpage_url')
        song.thumbnail = r.get('thumbnails')[0]['url']
        self.current_song = song

        logger.info(f"Playing song: {song.title} ({song.duration} seconds) requested by {song.requested_by}")
        self.guild.voice_client.play(
            discord.FFmpegPCMAudio(
                source = song.base_url,
                before_options = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
            ), 
            after = lambda x: self._next_song(channel)
        )
        await channel.send(embed=song.now_playing_embed())

        # loop = asyncio.get_event_loop()
        # for song in list(self.queue.playque)[:MAX_SONG_PRELOAD]:
        #     await asyncio.ensure_future(self.preload(song))
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
        # return discord.utils.get(bot.voice_clients, guild=itx.guild)
        try:
            bot_vc = discord.utils.get(bot.voice_clients, guild=itx.guild)
            return bot_vc.channel
        except AttributeError:
            return None
        
    async def is_connected(self, bot: discord.Client, itx: discord.Interaction):
        """Checks whether bot is connected to a VC"""
        guild = bot.get_guild(itx.guild_id)
        try:
            voice_channel = guild.voice_client.channel
            return voice_channel
        except:
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
