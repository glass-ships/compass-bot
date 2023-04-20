from pathlib import Path
from dataclasses import dataclass, field
from random import choice

import discord

# /path/to/compass-bot/src/compass_bot/
COMPASS_ROOT = Path(__file__).parent.parent

DEFAULT_PREFIX = ';' 

GLASS_HARBOR = 393995277713014785

def EMBED_COLOR():
    return choice([
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
    ])


@dataclass
class Emojis():
    eq = "<a:_eq:1011116489442598922>"
    cd = "<a:_music:1011116507587162122>"
    musicNote = "<a:_musicNote:1011101467576385556>"
    playlist = "<:_playlist:1011048129111543880>"
    shuffle = ":twisted_rightwards_arrows:"
    loop = "<:retweet:1011048385534496862>"
    catChillin = "<a:catChillin:1011104612733952011>"
    jar = ":jar:"
    compass = ":compass:"
    pause = ":pause_button:"
    play = ":arrow_forward:"
    previous = ":track_previous:"
    next = ":track_next:"


@dataclass
class GuildData:
    guild: discord.Guild
    guild_id: int = None #field(init=False)
    guild_name: str = None #field(init=False)
    prefix: str = ";"
    mem_role: int = 0
    dj_role: int = 0
    mod_roles: list = field(default_factory = list)
    default_channel: discord.TextChannel = None
    chan_bot: int = 0
    chan_logs: int =  0
    chan_welcome: int = 0
    chan_music: int = 0
    chan_lfg: int = 0
    chan_vids: int = 0
    videos_whitelist: list = field(default_factory = list)
    lfg: list = field(default_factory = list)

    def __post_init__(self):
        self.guild_id = self.guild.id
        self.guild_name = self.guild.name

        self.default_channel = self.guild.system_channel.id if self.guild.system_channel else None
        self.chan_bot = self.default_channel
        self.chan_logs = self.default_channel
        self.chan_welcome = self.default_channel
