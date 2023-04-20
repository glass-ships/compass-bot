import re

from yt_dlp import YoutubeDL
# from loguru import logger
# from bs4 import BeautifulSoup
# import httpx

from compass_bot.utils.utils import URL_REGEX, URL
from compass_bot.music.music_config import SUPPORTED_EXTENSIONS
from compass_bot.music.dataclasses import Sites, PlaylistTypes


guild_player = {}

###########################
### URL Parsing Methods ###
###########################

def extract_url(content):
    """Extracts URL from message content, or returns as is"""

    if re.search(URL_REGEX, content):
        result = URL_REGEX.search(content)
        url = result.group(0)
        if url.startswith("https://m."):
            url = url.replace("https://m.", "https://")
        # logger.info(f"Extracted URL: {url}")
        return url
    return None


def identify_host(url):
    """Returns Site type of url host"""

    # logger.info(f"Identifying Host for URL: {url}")
    url = URL(url)
    if any(url == i for i in SUPPORTED_EXTENSIONS):
        return Sites.Custom
    match url:
        case "https://www.youtu" | "https://youtu.be":
            return Sites.YouTube
        case "https://open.spotify":
            return Sites.Spotify
        case "bandcamp.com/track/":
            return Sites.Bandcamp
        case "soundcloud.com/":
            return Sites.SoundCloud
        case "https://twitter.com/":
            return Sites.Twitter
        case _:
            return Sites.Unknown


def identify_playlist(url):
    """Returns PlaylistType from url host"""
    
    url = URL(url)
    match url:
        case "playlist?list=":
            return PlaylistTypes.YouTube_Playlist
        case "https://open.spotify.com/playlist" | "https://open.spotify.com/album":
            return PlaylistTypes.Spotify_Playlist
        case "bandcamp.com/album/":
            return PlaylistTypes.BandCamp_Playlist
        case _:
            return PlaylistTypes.Not_Playlist

################################
### Spotify Metadata Methods ###
################################

def parse_spotify_track(sp, url: str) -> str:
    """Returns the artist and title for a given Spotify URL"""
    if "track" in url:
        track = sp.track(url)
        artists = [f"{a['name']}" for a in track['artists']]
        search = " - ".join([*artists, track['name']])
    return search


def parse_spotify_playlist(sp, url: str) -> tuple:
    """Returns a list of searches for a Spotify URL"""
    searches = []

    if "playlist" in url:
        offset = 0
        results = []
        playlist_title = sp.playlist(url)['name']
        while True:
            response = sp.playlist_items(
                playlist_id=url,
                offset=offset,
                fields='items.track.name, items.track.album.name, items.track.artists.name, total',
                additional_types=['track']
                )
            
            if len(response['items']) == 0:
                break
            
            results.append(response['items'])
            offset += len(response['items'])
        
        tracks = [i for sublist in results for i in sublist]
        for i in tracks:
            track = i['track']
            artists = [f"{a['name']}" for a in track['artists']]
            search = " ".join([*artists, track['name']])
            searches.append(search)

    if "album" in url:
        playlist_title = sp.album(url)['name']
        album_tracks = sp.album_tracks(url)['items']
        for track in album_tracks:
            artists = [f"{a['name']}" for a in track['artists']]
            search = " ".join([*artists, track['name']])
            searches.append(search)

    return playlist_title, searches

################################
### YouTube Metadata Methods ###
################################

def get_yt_metadata():
    return

def search_youtube(search_str):
    """Searches youtube for the video title and returns the first results video link"""

    with YoutubeDL() as ydl:
        r = ydl.extract_info(f"ytsearch1:{search_str}", download=False)
    
    if r == None: 
        return None

    # yt_id = r['entries'][0]['id']
    # url = f"https://www.youtube.com/watch?v={yt_id}"
    url = r['entries'][0]['original_url']
    return url

