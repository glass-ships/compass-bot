import re
from bs4 import BeautifulSoup
import spotipy

from classes.music.misc import *
from utils.utils import *
import utils.music_config as config

logger = get_logger(__name__)


guild_audiocontroller = {}
guild_settings = {}

# Connect to Spotify API
try:
    client_credentials_manager = spotipy.oauth2.SpotifyClientCredentials(client_id=config.SPOTIFY_ID, client_secret=config.SPOTIFY_SECRET)
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
    api = True
except:
    api = False
logger.info(f"Spotify API | User-Level Connection:{api}")

# Helper methods for parsing links

def clean_url(content):
    regex = re.compile(
        "http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

    if re.search(regex, content):
        result = regex.search(content)
        url = result.group(0)
        return url
    else:
        return None

def identify_host(url):
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

# Connection methods

def get_guild(bot, command):
    """
    Gets the guild a command belongs to (for VC commands). 
    Useful, if the command was sent via pm.
    """
    if command.guild is not None:
        return command.guild
    for guild in bot.guilds:
        for channel in guild.voice_channels:
            if command.author in channel.members:
                return guild
    return None

async def is_connected(ctx):
    """Checks whether bot is connected to a VC"""
    try:
        voice_channel = ctx.guild.voice_client.channel
        return voice_channel
    except:
        return None

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

async def play_check(ctx):
    """Checks that user is in a VC, and command was sent in appropriate channel"""

    settings = guild_settings[ctx.guild]
    cmd_channel = settings.get('command_channel')
    vc_rule = settings.get('user_must_be_in_vc')

    if cmd_channel != None:
        if cmd_channel != ctx.message.channel.id:
            await ctx.send(config.WRONG_CHANNEL_MESSAGE)
            return False

    #if vc_rule == True:
    author_voice = ctx.message.author.voice
    bot_vc = ctx.guild.voice_client.channel
    if author_voice == None:
        await ctx.send(config.USER_NOT_IN_VC_MESSAGE)
        return False
    elif ctx.message.author.voice.channel != bot_vc:
        await ctx.send(config.USER_NOT_IN_VC_MESSAGE)
        return False

async def convert_spotify(session, url):
    """Parses a spotify link for song info"""

    logger.info(f"Session: {session} - parsing Spotify link: {url}")

    if re.search(url_regex, url):
        result = url_regex.search(url)

        if "?si=" in url:
            url = result.group(0) + "&nd=1"
            logger.info(f"Parsed url: {url}")

    logger.info("Awaiting response...")

    try:
        async with session.get(url) as response:
            page = await response.text()
            
            logger.info(f"Parsing response")

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
    """
    Parses a Spotify playlist link
    Returns: Spotify_Playlist class
    """

    code = url.split('/')[4].split('?')[0]

    if api == True:

        if "open.spotify.com/album" in url:
            try:
                results = sp.album_tracks(code)
                tracks = results['items']

                while results['next']:
                    results = sp.next(results)
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
                results = sp.playlist_items(code)
                tracks = results['items']
                while results['next']:
                    results = sp.next(results)
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

