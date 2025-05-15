from dataclasses import dataclass
from enum import StrEnum, auto
from datetime import timedelta
from typing import Optional

import discord

from compass_bot.utils.bot_config import EMBED_COLOR, Emojis


class Sites(StrEnum):
    Spotify = auto()
    YouTube = auto()
    Twitter = auto()
    SoundCloud = auto()
    Bandcamp = auto()
    Custom = auto()
    Unknown = auto()


class PlaylistTypes(StrEnum):
    Spotify_Playlist = auto()
    YouTube_Playlist = auto()
    BandCamp_Playlist = auto()
    Not_Playlist = auto()


@dataclass
class Search:
    query: str
    url: str = None
    original_url: str = None


@dataclass
class UserSearch:
    query: str
    url: Optional[str]
    playlist_type: PlaylistTypes
    host: Sites


@dataclass
class YouTubeSearchResults:
    title: str
    url: str


@dataclass
class Playlist:
    name: str
    total: int
    items: list


@dataclass
class Song:
    """Dataclass for a song object

    For additional info about ceratin attributes, see: https://github.com/yt-dlp/yt-dlp

    Attributes:
        host (str): The host of the song (e.g. YouTube, Spotify)
        requested_by (str): The user who requested the song
        original_url (str): The original URL of the song provided by the user
        base_url (str): The URL returned by `music_utils.search_youtube`
        webpage_url (str): The URL by music_utils.search_youtube
        channel_name (str): The name of the channel that uploaded the song
        title (str): The title of the song
        duration (str): The duration of the song
        thumbnail (str): The thumbnail of the song
    """

    host: str = None
    requested_by: str = None
    original_url: str = None
    base_url: str = None
    webpage_url: str = None
    channel_name: str = None
    title: str = None
    duration: str = None
    thumbnail: str = None
    # output: str = ""

    def queued_embed(self, pos: int = None):
        # TODO: Add estimated time until song is played
        embed = discord.Embed(
            description=f"{Emojis.catChillin} Song queued: {pos}. [{self.title}]({self.webpage_url})",
            color=EMBED_COLOR(),
        )
        return embed

    def now_playing_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"{Emojis.eq} Now Playing",
            description=f"[{self.title}]({self.original_url})" if self.original_url is not None else self.title,
            color=EMBED_COLOR(),
        )
        if self.thumbnail is not None:
            embed.set_thumbnail(url=self.thumbnail)
        embed.add_field(name="Uploader:", value=self.channel_name, inline=True)
        embed.add_field(
            name="Length: ",
            value=f"`{str(timedelta(seconds=self.duration))}`" if self.duration is not None else "`Unknown`",
            inline=True,
        )
        embed.add_field(name="Requested by:", value=self.requested_by.mention, inline=True)
        embed.set_footer(icon_url=self.requested_by.avatar.url)

        return embed
