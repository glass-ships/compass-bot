import os
from pathlib import Path

src_path = Path(__file__).parent.parent

DEFAULT_PREFIX = ';' 

HELP = """
Compass Bot
------------
Description: 
    A General use Discord bot with features for moderation, music, Destiny, and more. 

Usage: 
    python src/main.py [-h, --help] [-d, --dev]
    
Optional Arguments:
  -h, --help  Show this help message and exit
  -d, --dev   Run the development version of the Bot locally 
"""

EMBED_COLORS = [
    0xA575FF, 
    0xFF23E9, 
    0x37F3E4, 
    0x7E6C6C, 
    0xEBC280  
]

def default_guild_data(guild):
    default_channel = guild.system_channel.id if guild.system_channel else None
    return {
    "guild_id": guild.id, 
    "guild_name": guild.name,
    "prefix": ";",
    "mod_roles": [],
    "mem_role": 0,
    "dj_role": 0,
    "chan_bot": default_channel,
    "chan_logs": default_channel,
    "chan_music": 0,
    "chan_vids": 0,
    "chan_lfg": 0,
    "videos_whitelist": [],
    "lfg": []
    }
