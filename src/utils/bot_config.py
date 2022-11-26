import os
from pathlib import Path
from dataclasses import dataclass, field
import discord

src_path = Path(__file__).parent.parent


DEFAULT_PREFIX = ';' 

GLASS_HARBOR = 393995277713014785

EMBED_COLORS = [
    0xA575FF, 
    0xFF23E9, 
    0x37F3E4, 
    0x7E6C6C, 
    0xEBC280  
]

HELP = """
Compass Bot
------------
Description: 
    A General use Discord bot with features for moderation, music, Destiny, and more. 

Usage: 
    python src/main.py [--help] [--dev] [--debug]
    
Optional Arguments:
  --help  Show this help message and exit
  --dev   Run the development version of the Bot locally 
  --debug Set logging level to DEBUG
"""

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
