import re
from enum import Enum
import asyncio, aiohttp
from bs4 import BeautifulSoup

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

import utils.music_config as config
from utils.helper import *

logger = get_logger(__name__)
#####

# A dictionary that remembers which guild belongs to which audiocontroller
guild_to_audiocontroller = {}

# A dictionary that remembers which settings belongs to which guild
guild_to_settings = {}

url_regex = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")


#async def get_session():
#    return aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'})
#session = get_session()
#print(f"Session: {session}")

try:
    sp_api = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=config.SPOTIFY_ID, client_secret=config.SPOTIFY_SECRET))
    api = True
except:
    api = False


class Timer:
    def __init__(self, callback):
        self._callback = callback
        self._task = asyncio.create_task(self._job())

    async def _job(self):
        await asyncio.sleep(config.VC_TIMEOUT)
        await self._callback()

    def cancel(self):
        self._task.cancel()


class Sites(Enum):
    Spotify = "Spotify"
    Spotify_Playlist = "Spotify Playlist"
    YouTube = "YouTube"
    Twitter = "Twitter"
    SoundCloud = "SoundCloud"
    Bandcamp = "Bandcamp"
    Custom = "Custom"
    Unknown = "Unknown"


class Playlist_Types(Enum):
    Spotify_Playlist = "Spotify Playlist"
    YouTube_Playlist = "YouTube Playlist"
    BandCamp_Playlist = "BandCamp Playlist"
    Unknown = "Unknown"


class Origins(Enum):
    Default = "Default"
    Playlist = "Playlist"


# Helper methods for links

def get_guild(bot, command):
    """Gets the guild a command belongs to. Useful, if the command was sent via pm."""
    if command.guild is not None:
        return command.guild
    for guild in bot.guilds:
        for channel in guild.voice_channels:
            if command.author in channel.members:
                return guild
    return None


def get_url(content):

    regex = re.compile(
        "http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

    if re.search(regex, content):
        result = regex.search(content)
        url = result.group(0)
        return url
    else:
        return None


def identify_url(url):
    if url is None:
        return Sites.Unknown

    if "https://www.youtu" in url or "https://youtu.be" in url:
        return Sites.YouTube

    if "https://open.spotify.com/track" in url:
        return Sites.Spotify

    if "https://open.spotify.com/playlist" in url or "https://open.spotify.com/album" in url:
        return Sites.Spotify_Playlist

    if "bandcamp.com/track/" in url:
        return Sites.Bandcamp

    if "https://twitter.com/" in url:
        return Sites.Twitter

    if url.lower().endswith(config.SUPPORTED_EXTENSIONS):
        return Sites.Custom

    if "soundcloud.com/" in url:
        return Sites.SoundCloud

    # If no match
    return Sites.Unknown


def identify_playlist(url):
    if url is None:
        return Sites.Unknown

    if "playlist?list=" in url:
        return Playlist_Types.YouTube_Playlist

    if "https://open.spotify.com/playlist" in url or "https://open.spotify.com/album" in url:
        return Playlist_Types.Spotify_Playlist

    if "bandcamp.com/album/" in url:
        return Playlist_Types.BandCamp_Playlist

    return Playlist_Types.Unknown


def clean_sclink(track):
    if track.startswith("https://m."):
        track = track.replace("https://m.", "https://")
    if track.startswith("http://m."):
        track = track.replace("http://m.", "https://")
    return track


async def connect_to_channel(guild, dest_channel_name, ctx, switch=False, default=True):
    """Connects the bot to the specified voice channel.
        Args:
            guild: The guild for witch the operation should be performed.
            switch: Determines if the bot should disconnect from his current channel to switch channels.
            default: Determines if the bot should default to the first channel, if the name was not found.
    """
    for channel in guild.voice_channels:
        if str(channel.name).strip() == str(dest_channel_name).strip():
            if switch:
                try:
                    await guild.voice_client.disconnect()
                except:
                    await ctx.send(config.NOT_CONNECTED_MESSAGE)

            await channel.connect()
            return

    if default:
        try:
            await guild.voice_channels[0].connect()
        except:
            await ctx.send(config.DEFAULT_CHANNEL_JOIN_FAILED)
    else:
        await ctx.send(config.CHANNEL_NOT_FOUND_MESSAGE + str(dest_channel_name))


async def is_connected(ctx):
    try:
        voice_channel = ctx.guild.voice_client.channel
        return voice_channel
    except:
        return None


async def play_check(ctx):

    sett = guild_to_settings[ctx.guild]

    cm_channel = sett.get('command_channel')
    vc_rule = sett.get('user_must_be_in_vc')

    if cm_channel != None:
        if cm_channel != ctx.message.channel.id:
            await ctx.send(config.WRONG_CHANNEL_MESSAGE)
            return False

    if vc_rule == True:
        author_voice = ctx.message.author.voice
        bot_vc = ctx.guild.voice_client.channel
        if author_voice == None:
            await ctx.send(config.USER_NOT_IN_VC_MESSAGE)
            return False
        elif ctx.message.author.voice.channel != bot_vc:
            await ctx.send(config.USER_NOT_IN_VC_MESSAGE)
            return False


async def convert_spotify(session, url):
    async with session as s:
        logger.info(f"Session: {s} - parsing Spotify link: {url}")

        if re.search(url_regex, url):
            result = url_regex.search(url)

            if "?si=" in url:
                url = result.group(0) + "&nd=1"
                logger.info(f"Parsed url: {url}")

        logger.info("Awaiting response...")
        response = await s.get(url)
        logger.error(f"Something went wrong: {e}")

        try:
            page = await response.text()
            
            logger.info(f"Got response: {page}")

            soup = BeautifulSoup(page, 'html.parser')

            title = soup.find('title')
            title = title.string
            title = title.replace('- song by', '')
            title = title.replace('| Spotify', '')
        except Exception as e:
            logger.error(f"Something went wrong: {e}")
            return e
        return title

async def get_spotify_playlist(session, url):
    """Return Spotify_Playlist class"""

    code = url.split('/')[4].split('?')[0]

    if api == True:

        if "open.spotify.com/album" in url:
            try:
                results = sp_api.album_tracks(code)
                tracks = results['items']

                while results['next']:
                    results = sp_api.next(results)
                    tracks.extend(results['items'])

                links = []

                for track in tracks:
                    try:
                        links.append(track['external_urls']['spotify'])
                    except:
                        pass
                return links
            except:
                if config.SPOTIFY_ID != "" or config.SPOTIFY_SECRET != "":
                    logger.error("ERROR: Check spotify CLIENT_ID and SECRET")

        if "open.spotify.com/playlist" in url:
            try:
                results = sp_api.playlist_items(code)
                tracks = results['items']
                while results['next']:
                    results = sp_api.next(results)
                    tracks.extend(results['items'])

                links = []

                for track in tracks:
                    try:
                        links.append(
                            track['track']['external_urls']['spotify'])
                    except:
                        pass
                return links

            except:
                if config.SPOTIFY_ID != "" or config.SPOTIFY_SECRET != "":
                    logger.error("ERROR: Check spotify CLIENT_ID and SECRET")

    async with session.get(url + "&nd=1") as response:
         page = await response.text()

    soup = BeautifulSoup(page, 'html.parser')

    results = soup.find_all(property="music:song", attrs={"content": True})

    links = []

    for item in results:
        links.append(item['content'])

    title = soup.find('title')
    title = title.string

    return links



