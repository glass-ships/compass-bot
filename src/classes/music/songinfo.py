import datetime

import discord
import utils.music_config as config
from random import choice

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
        self.info = self.Sinfo(requested_by, uploader, title, duration, webpage_url, thumbnail)

    class Sinfo:
        def __init__(self, requested_by, uploader, title, duration, webpage_url, thumbnail):
            self.requested_by = requested_by
            self.uploader = uploader
            self.title = title
            self.duration = duration
            self.webpage_url = webpage_url
            self.thumbnail = thumbnail
            self.output = ""

        def format_output(self, playtype):

            embed = discord.Embed(title=playtype, description="<a:music:986166508843569172> [{}]({})".format(self.title, self.webpage_url), color=choice(config.EMBED_COLORS))

            if self.thumbnail is not None:
                embed.set_thumbnail(url=self.thumbnail)

            embed.add_field(
                name=config.SONGINFO_UPLOADER,
                value=self.uploader,
                inline=True
                )

            if self.duration is not None:
                embed.add_field(
                    name=config.SONGINFO_DURATION,
                    value="`{}`".format(str(datetime.timedelta(seconds=self.duration))),
                    inline=True
                )
            else:
                embed.add_field(
                    name=config.SONGINFO_DURATION,
                    value=f"`{config.SONGINFO_UNKNOWN_DURATION}`",
                    inline=True
                )

            embed.add_field(
                name="Requested by:",
                value=self.requested_by.mention,
                inline=True
            )

            embed.set_footer(
                text=choice(footers),
                icon_url=self.requested_by.avatar.url
            )

            return embed