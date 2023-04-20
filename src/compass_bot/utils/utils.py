import os
import time, re
from pathlib import Path
from typing import Optional, Union
from datetime import datetime
from dateutil import tz

import discord
import shlex

from compass_bot.utils.bot_config import EMBED_COLOR

URL_REGEX = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

class URL(str):
    def __eq__(self, other) -> bool:
        return self.__contains__(other)


from rich.console import Console
console = Console(
    color_system="truecolor",
    stderr=True,
    style="blue1",
)


class ddict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

def parse_args(args: str) -> ddict:
    """Parse arguments from a string into a dictionary"""
    
    args = shlex.split(args)
    opts = {}
    for i in range(len(args)):
        arg = args[i]
        if arg.startswith('--'):
            opts[arg.lstrip('-').replace('-','_')] = args[i+1]
    return ddict(opts)

def get_emojis(guild):
    """Returns lists of all static and animated emojis in a guild"""

    emojis = {'anim': [], 'static': []}
    for i in guild.emojis:
        if i.animated == True:
            emojis['anim'].append(i)
        else:
            emojis['static'].append(i)
    return emojis['static'], emojis['anim']


async def download(itx, attachment, path: Optional[Union[str, os.PathLike]]) -> None:
    """Download an attachment from a message"""

    fp = os.path.join("downloads", itx.guild.name, path)
    fn = attachment.filename
    Path(fp).mkdir(parents=True, exist_ok=True)
    await attachment.save(fp=f"{fp}/{fn}")
    return


def getfilepath(itx, fp) -> str:
    """Returns filepath with guild-specific download prefix"""

    return f"downloads/{itx.guild.name}/{fp}"


def check_time_format(t):
    """Check that datetime input is in format `YYYY-MM-DD HH:MM AM/PM TZ`"""

    pattern = r"\d{4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{2}\s[a-zA-Z]{2}\s[a-zA-Z]{3}"
    match = re.match(pattern, t)
    return bool(match)


def dt_to_epoch(t):
    """Convert datetime to epoch time (format: `YYYY-MM-DD HH:MM AM/PM TZ`)"""

    msg_split = t.split()
    temp = []
    temp.extend(msg_split[0].split('-'))
    temp.extend(msg_split[1].split(':'))
    temp.append(msg_split[2])
    stream_tz = tz.gettz(msg_split[3])
    dt = datetime(int(temp[0]),int(temp[1]), int(temp[2]), int(temp[3]), int(temp[4]), tzinfo=stream_tz)
    et = int(time.mktime(dt.timetuple()))
    return et

async def send_embed(*, channel: discord.TextChannel, title=None, description=None, image=None, thumbnail=None, footer=None, footer_image=None):
        """Send embed to channel"""

        embed = discord.Embed(title=title, description=description, color = EMBED_COLOR())

        if image:
            embed.set_image(url=image)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        if footer or footer_image:
            embed.set_footer(text=footer, icon_url=footer_image)
        
        await channel.send(embed=embed)
        return