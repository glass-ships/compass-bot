import os
from pathlib import Path

ABSOLUTE_PATH = '' # DO NOT MODIFY
ROOT_DIR = f"{Path(__file__).parent.parent.parent}/.generated"

SPOTIFY_ID: str = os.getenv('SPOTIFY_ID')
SPOTIFY_SECRET: str = os.getenv('SPOTIFY_SECRET')

#### Bot settings
SUPPORTED_EXTENSIONS = ('.webm', '.mp4', '.mp3', '.avi', '.wav', '.m4v', '.ogg', '.mov')
COOKIE_PATH = f"{ROOT_DIR}/cookies.txt"
MAX_SONG_PRELOAD = 5                # maximum of 25
ALLOW_VC_TIMEOUT_EDIT = True        # allow or disallow editing the vc_timeout guild setting
VC_TIMEOUT = 60                     # seconds
VC_TIMOUT_DEFAULT = True            # Timeout by DefaultTrue/False 
MAX_HISTORY_LENGTH = 10             # Number of songs to keep in history
MAX_TRACKNAME_HISTORY_LENGTH = 15   # Not sure how this is different?


### Error messages
ALREADY_CONNECTED_MESSAGE = "Error: Already connected to a voice channel"
CHANNEL_NOT_FOUND_MESSAGE = "Error: Could not find channel"
DEFAULT_CHANNEL_JOIN_FAILED = "Error: Could not join the default voice channel"
INVALID_INVITE_MESSAGE = "Error: Invalid invitation link"
NO_GUILD_MESSAGE = 'Error: Please join a voice channel or enter the command in guild chat'
NOT_CONNECTED_MESSAGE = "Error: Compass is not connected to any voice channel"
USER_NOT_IN_VC_MESSAGE = "Error: Please join the active voice channel to use commands"
WRONG_CHANNEL_MESSAGE = "Error: Please use the correct command channel"


### Track info formatting
INFO_HISTORY_TITLE = "Songs Played:"
SONGINFO_UPLOADER = "Song by: "
SONGINFO_DURATION = "Length: "
SONGINFO_SECONDS = "s"
SONGINFO_LIKES = "Likes: "
SONGINFO_DISLIKES = "Dislikes: "
SONGINFO_NOW_PLAYING = "Now Playing"
SONGINFO_QUEUE_ADDED = "Added to queue"
SONGINFO_PLAYLIST_QUEUED = "Queued playlist <a:catChillin:1011104612733952011>"
SONGINFO_ERROR = "Error: Unsupported site or age restricted content. To enable age restricted content check the documentation/wiki."
SONGINFO_UNKNOWN_DURATION = "Unknown"


### Help messages
HELP_CHANGECHANNEL = "Move the bot to your voice channel."
HELP_CLEAR = "Clear the queue and skips the current song."
HELP_CONNECT = "Connect the bot to your voice channel."
HELP_DISCONNECT = "Disconnect bot from voice channel."
HELP_HISTORY = "Show the last " + str(MAX_TRACKNAME_HISTORY_LENGTH) + " songs played."
HELP_LOOP = "Loop the currently playing song and locks the queue. Toggle on/off."
HELP_MOVE = 'Move a track in the queue.'
HELP_PAUSE = "Pause playback (continue with `resume`)."
HELP_PLAY = "Play a song or playlist (keyword search or supported link)"
HELP_PREV = "Play the previous song again."
HELP_QUEUE = "Show the current song queue."
HELP_REMOVE = 'Remove the song at the given index.'
HELP_RESUME = "Resume playback."
HELP_SHUFFLE = "Shuffle the queue (irreversible!)"
HELP_SKIP = "Skip the current song"
HELP_SKIPTO = "Skips to the specified position in the queue"
HELP_SONGINFO = "Show info about current Song"
HELP_STOP = "Stop playback and clear the queue"
HELP_VOL = "Change the volume (0-100%)"
HELP_VOL_SHORT = "Change volume %"
