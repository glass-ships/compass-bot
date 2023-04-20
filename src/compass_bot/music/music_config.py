import os
from dataclasses import dataclass
from enum import StrEnum, auto
# from pathlib import Path

from compass_bot.utils.bot_config import COMPASS_ROOT

# Re-usable paths
ABSOLUTE_PATH = '' # DO NOT MODIFY
GENERATED_FILES = COMPASS_ROOT / '.generated'

# Spotify API
SPOTIFY_ID: str = os.getenv('SPOTIFY_ID')
SPOTIFY_SECRET: str = os.getenv('SPOTIFY_SECRET')

# Bot settings
SUPPORTED_EXTENSIONS = ('.webm', '.mp4', '.mp3', '.avi', '.wav', '.m4v', '.ogg', '.mov')
COOKIE_PATH = f"{GENERATED_FILES}/cookies.txt"
MAX_SONG_PRELOAD = 5                # maximum of 25
ALLOW_VC_TIMEOUT_EDIT = False       # allow or disallow editing the vc_timeout guild setting
VC_TIMEOUT = 60                     # in seconds - 0 for no timeout?
MAX_HISTORY_LENGTH = 10             # Number of songs to keep in history
MAX_TRACKNAME_HISTORY_LENGTH = 15   # Not sure how this is different?

# Youtube-dl options
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'title': True,
    "cookiefile": COOKIE_PATH,
    'default_search': 'auto',
    'extract_flat': 'in_playlist',
    'noplaylist': True,
    'quiet': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

# Error messages
@dataclass
class ErrorMessages():
    SEARCH_ERROR = ":exclamation: Error processing search request."
    NO_USER_VC = ":exclamation: User is not in a voice channel. Please join a VC and try again."
    NO_GUILD = ':exclamation: Please join a voice channel or enter the command in guild chat'
    CHANNEL_NOT_FOUND_MESSAGE = ":exclamation: Could not find channel"
    DEFAULT_CHANNEL_JOIN_FAILED = ":exclamation: Could not join the default voice channel"
    INVALID_INVITE_MESSAGE = ":exclamation: Invalid invitation link"
    NOT_CONNECTED_MESSAGE = ":exclamation: Compass is not connected to any voice channel"
    WRONG_CHANNEL_MESSAGE = ":exclamation: Please use the correct command channel"
    
    def WRONG_USER_VC(vc):
        return f":exclamation: Bot already connected to <#{vc.id}>. Please use the `/join` command, or move/disconnect Compass and try again."

# Track info formatting
# class TrackInfo(StrEnum):
#     QUEUED_PLAYLIST = "Queued playlist <a:catChillin:1011104612733952011>"
#     SONGINFO_NOW_PLAYING = "Now Playing"
#     SONGINFO_QUEUE_ADDED = "Added to queue"
#     SONGINFO_ERROR = ":exclamation: Unsupported site or age restricted content. To enable age restricted content check the documentation/wiki."
#     SONGINFO_SECONDS = "s"
#     SONGINFO_LIKES = "Likes: "
#     SONGINFO_DISLIKES = "Dislikes: "

