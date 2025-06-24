from pathlib import Path
from dataclasses import dataclass, field
from random import choice
from typing import List, Optional

import discord

# /path/to/compass-bot/src/compass/
COMPASS_ROOT = Path(__file__).parent.parent.parent.parent
COMPASS_SRC = Path(__file__).parent.parent

DEFAULT_PREFIX = ";"
GLASS = 357738904591532033
GLASS_HARBOR = 393995277713014785

exclude_modules = ["__init__", "pinarchiver"]
MODULES = [f.stem for f in Path(COMPASS_SRC / "cogs").glob("*.py") if f.stem not in exclude_modules]
CHANNEL_OPTIONS = ["logs", "bot", "welcome", "music", "lfg", "videos"]  # , 'pins']
ROLE_OPTIONS = ["mod", "member", "required"]


class COLORS:
    black = discord.Colour.from_str("#272932")
    red = discord.Colour.from_str("#710000")
    yellow = discord.Colour.from_str("#f3e500")
    cyan = discord.Colour.from_str("#1ac5b0")
    blue = discord.Colour.from_str("#3e7bf3")
    purple = discord.Colour.from_str("#9370db")
    pink = discord.Colour.from_str("#e455ae")
    magenta = discord.Colour.from_str("#cb1dcd")
    pale_silver = discord.Colour.from_str("#d1c5c0")

    @staticmethod
    def random():
        return choice(
            [
                COLORS.red,
                COLORS.yellow,
                COLORS.cyan,
                COLORS.blue,
                COLORS.purple,
                COLORS.pink,
                COLORS.magenta,
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
    guild_id: Optional[int] = None
    guild_name: Optional[str] = None
    default_channel: Optional[int] = None
    chan_bot: Optional[int] = None
    chan_lfg: Optional[int] = None
    chan_logs: Optional[int] = None
    chan_music: Optional[int] = None
    chan_vids: Optional[int] = None
    chan_welcome: Optional[int] = None
    mem_role: Optional[int] = None
    mod_roles: List[str] = field(default_factory=list)
    prefix: str = DEFAULT_PREFIX
    required_roles: List[str] = field(default_factory=list)
    track_activity: bool = False
    videos_whitelist: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.guild_id = self.guild.id
        self.guild_name = self.guild.name
        self.default_channel = self.guild.system_channel.id if self.guild.system_channel else None
        # self.chan_bot = self.chan_bot if self.chan_bot else self.default_channel
        # self.chan_logs = self.chan_logs if self.chan_logs else self.default_channel
        # self.chan_welcome = self.chan_welcome if self.chan_welcome else self.default_channel
