from dataclasses import dataclass
from enum import StrEnum, auto
from datetime import timedelta

import discord

from compass.config.bot_config import COLORS, Emojis


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
    host: str = None
    original_url: str = None
    base_url: str = None
    requested_by: str = None
    channel_name: str = None
    title: str = None
    duration: str = None
    webpage_url: str = None
    thumbnail: str = None
    output: str = ""

    def queued_embed(self, pos: int = None):
        # TODO: Add estimated time until song is played
        embed = discord.Embed(
            description=f"{Emojis.catChillin} Song queued: {pos}. [{self.title}]({self.webpage_url})",
            color=COLORS().random(),
        )
        return embed

    def now_playing_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"{Emojis.eq} Now Playing",
            description=f"[{self.title}]({self.original_url})" if self.original_url is not None else self.title,
            color=COLORS().random(),
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
