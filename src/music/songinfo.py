import discord

import datetime
from random import choice

from utils.bot_config import EMBED_COLORS
from music.music_config import *

footers = [
    '☆꧁✬◦°˚°◦. -- .◦°˚°◦✬꧂☆',
    '*¸ „„.•~¹°”ˆ˜¨♡ -- ♡¨˜ˆ”°¹~•.„¸*',
    '(¯`’•.¸❤♫♪♥(◠‿◠)♥♫♪❤¸.•’´¯)',
    '¸.·✩·.¸¸.·¯⍣✩ - ✩⍣¯·.¸¸.·✩·.¸',
    '♫♪♩·.¸¸.·♩♪♫ -- ♫♪♩·.¸¸.·♩♪♫',
]

class Song():
    def __init__(self, origin, host, base_url=None, requested_by=None, uploader=None, title=None, duration=None, webpage_url=None, thumbnail=None):
        self.host = host
        self.origin = origin
        self.base_url = base_url
        self.info = SongInfo(requested_by, uploader, title, duration, webpage_url, thumbnail)

class SongInfo:
    def __init__(self, requested_by=None, uploader=None, title=None, duration=None, webpage_url=None, thumbnail=None):
        self.requested_by = requested_by
        self.uploader = uploader
        self.title = title
        self.duration = duration
        self.webpage_url = webpage_url
        self.thumbnail = thumbnail
        self.output = ""

    def format_output(self, playtype, *, pos: int = None):

        if playtype == SONGINFO_QUEUE_ADDED:
            embed = discord.Embed(description=f"<a:_musicNote:1011101467576385556> Song queued: {pos}. [{self.title}]({self.webpage_url})", color=choice(EMBED_COLORS))
        else:    
            embed = discord.Embed(title="Now Playing", description=f"<a:_music:1011116507587162122> [{self.title}]({self.webpage_url})", color=choice(EMBED_COLORS))

            if self.thumbnail is not None:
                embed.set_thumbnail(url=self.thumbnail)

            embed.add_field(
                name=SONGINFO_UPLOADER,
                value=self.uploader,
                inline=True
                )

            if self.duration is not None:
                embed.add_field(name=SONGINFO_DURATION, value=f"`{str(datetime.timedelta(seconds=self.duration))}`", inline=True)
            else:
                embed.add_field(name=SONGINFO_DURATION, value=f"`{SONGINFO_UNKNOWN_DURATION}`", inline=True)

            embed.add_field(name="Requested by:", value=self.requested_by.mention, inline=True)

            embed.set_footer(
                text=choice(footers),
                icon_url=self.requested_by.avatar.url)

        return embed