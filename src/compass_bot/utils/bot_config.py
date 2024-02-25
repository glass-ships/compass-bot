from pathlib import Path
from dataclasses import dataclass, field
from random import choice
from typing import List

import discord

# /path/to/compass-bot/src/compass_bot/
COMPASS_ROOT = Path(__file__).parent.parent.parent.parent
COMPASS_SRC = Path(__file__).parent.parent

DEFAULT_PREFIX = ";"
GLASS = 357738904591532033
GLASS_HARBOR = 393995277713014785


def EMBED_COLOR():
    return choice(
        [
            discord.Colour.magenta(),
            discord.Colour.blurple(),
            discord.Colour.dark_teal(),
            discord.Colour.blue(),
            discord.Colour.dark_blue(),
            discord.Colour.dark_gold(),
            discord.Colour.dark_green(),
            discord.Colour.dark_grey(),
            discord.Colour.dark_magenta(),
            discord.Colour.dark_orange(),
            discord.Colour.dark_purple(),
            discord.Colour.dark_red(),
            discord.Colour.darker_grey(),
            discord.Colour.gold(),
            discord.Colour.green(),
            discord.Colour.greyple(),
            discord.Colour.orange(),
            discord.Colour.purple(),
        ]
    )


@dataclass
class Emojis:
    # Music Emojis
    catChillin = "<a:catChillin:1011104612733952011>"
    cd = "<a:_music:1011116507587162122>"
    eq = "<a:_eq:1011116489442598922>"
    loop = "<:retweet:1011048385534496862>"
    musicNote = "<a:_musicNote:1011101467576385556>"
    playlist = "<:_playlist:1011048129111543880>"
    shuffle = ":twisted_rightwards_arrows:"
    compass = ":compass:"
    jar = ":jar:"
    next = ":track_next:"
    pause = ":pause_button:"
    play = ":arrow_forward:"
    previous = ":track_previous:"


@dataclass
class GuildData:
    guild: discord.Guild
    chan_bot: int = None
    chan_lfg: int = None
    chan_logs: int = None
    chan_music: int = None
    chan_vids: int = None
    chan_welcome: int = None
    default_channel: discord.TextChannel = None
    guild_id: int = None  # field(init=False)
    guild_name: str = None  # field(init=False)
    mem_role: int = None
    mod_roles: List[str] = field(default_factory=list)
    prefix: str = ";"
    required_roles: List[str] = field(default_factory=list)
    videos_whitelist: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.guild_id = self.guild.id
        self.guild_name = self.guild.name
        self.default_channel = self.guild.system_channel.id if self.guild.system_channel else None
        # self.chan_bot = self.chan_bot if self.chan_bot else self.default_channel
        # self.chan_logs = self.chan_logs if self.chan_logs else self.default_channel
        # self.chan_welcome = self.chan_welcome if self.chan_welcome else self.default_channel


class CustomException(Exception):
    pass
    # def __init__(self, message, errors):
    #     super().__init__(message)
    #     self.errors = errors


class FetchException(CustomException):
    pass


class QueueException(CustomException):
    pass
