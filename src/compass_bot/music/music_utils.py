# from bs4 import BeautifulSoup
# from loguru import logger
# import httpx
# from yt_dlp import YoutubeDL

from compass_bot.utils.utils import URL
from compass_bot.music.music_config import SUPPORTED_EXTENSIONS
from compass_bot.music.dataclasses import Sites, Search, Playlist, PlaylistTypes, YouTubeSearchResults
import compass_bot.music.yt_utils as yt_utils

guild_player = {}

###########################
### URL Parsing Methods ###
###########################


def identify_host(url):
    """Returns Site type of url host"""

    # logger.info(f"Identifying Host for URL: {url}")
    # url = URL(url)
    if any(url == i for i in SUPPORTED_EXTENSIONS):
        return Sites.Custom
    match URL(url):
        case "https://www.youtu" | "https://youtu.be":
            return Sites.YouTube
        case "https://open.spotify":
            return Sites.Spotify
        case "bandcamp.com/":
            return Sites.Bandcamp
        case "soundcloud.com/":
            return Sites.SoundCloud
        case "twitter.com/":
            return Sites.Twitter
        case _:
            return Sites.Unknown


def identify_playlist(url):
    """Returns PlaylistType from url host"""

    # url = URL(url)
    match URL(url):
        case "playlist?list=" | "&list=":
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


def parse_spotify_track(sp, url: str) -> Search:
    """Returns the artist and title for a given Spotify URL"""
    if "track" in url:
        track = sp.track(url)
        artists = [f"{a['name']}" for a in track["artists"]]
        search = Search(query=" - ".join([*artists, track["name"]]), url=url)
        return search


def parse_spotify_playlist(sp, url: str) -> Playlist:
    """Returns a list of searches for a Spotify URL"""

    searches = []

    if "album" in url:
        playlist_title = sp.album(url)["name"]
        album_tracks = sp.album_tracks(url)["items"]
        for track in album_tracks:
            artists = [f"{a['name']}" for a in track["artists"]]
            sp_url = track["external_urls"]["spotify"]
            searches.append(Search(query=" ".join([*artists, track["name"]]), url=sp_url))
    elif "playlist" in url:
        offset = 0
        results = []
        playlist_title = sp.playlist(url)["name"]
        while True:
            response = sp.playlist_items(
                playlist_id=url,
                offset=offset,
                fields=",".join(
                    [
                        "items.track.name",
                        "items.track.album.name",
                        "items.track.artists.name",
                        "items.track.external_urls.spotify",
                        "total",
                    ]
                ),
                additional_types=["track"],
            )

            if len(response["items"]) == 0:
                break

            results.append(response["items"])
            offset += len(response["items"])

        tracks = [i for sublist in results for i in sublist]
        for t in tracks:
            track = t["track"]
            artists = [f"{a['name']}" for a in track["artists"]]
            sp_url = track["external_urls"]["spotify"]
            searches.append(Search(query=" ".join([*artists, track["name"]]), url=sp_url))
    else:
        return None
    return Playlist(name=playlist_title, total=len(searches), items=searches)


################################
### YouTube Metadata Methods ###
################################


def search_youtube(query: str):
    """Searches youtube for the video title and returns the first result"""
    # with YoutubeDL({'skip_download': True}) as ydl:
    #     r = ydl.extract_info(f"ytsearch1:{search_str}", download=False)
    # return None if r is None else r['entries'][0]['original_url']
    # query = (''.join(query)).encode('utf-8')
    video = yt_utils.SearchYT(query, limit=1).videos()[0]
    return YouTubeSearchResults(title=video["title"], url=f"https://www.youtube.com/watch?v={video['id']}")


def get_yt_metadata(yt_url):
    """Returns the metadata for a given YouTube URL"""
    # with YoutubeDL({'skip_download': True, 'quiet': True}) as ydl:
    #     r = ydl.extract_info(yt_url, download=False)
    # return r
    data = yt_utils.Data(yt_url).data()
    return data


# def download_video(url):
#     if song.title != None:
#             return

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
