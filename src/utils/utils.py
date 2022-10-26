#### Import libraries ###

import discord
from discord.utils import get

import os, sys
from pathlib import Path
from typing import Optional, Union

import time, re, asyncio
from datetime import datetime
from dateutil import tz

import logging

url_regex = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

##### Helper Functions #####

def get_emojis(guild):
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
    """Normalize a downloaded filepath"""
    return f"downloads/{itx.guild.name}/{fp}"


def check_time_format(t):
    """Assert datetime format  """
    pattern = r"\d{4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{2}\s[a-zA-Z]{2}\s[a-zA-Z]{3}"
    match = re.match(pattern, t)
    return bool(match)

def dt_to_epoch(t):
    """Convert datetime to epoch time. Assumes format 'YYYY-MM-DD HH:MM AM/PM TZ'"""
    msg_split = t.split()
    temp = []
    temp.extend(msg_split[0].split('-'))
    temp.extend(msg_split[1].split(':'))
    temp.append(msg_split[2])
    stream_tz = tz.gettz(msg_split[3])
    dt = datetime(int(temp[0]),int(temp[1]), int(temp[2]), int(temp[3]), int(temp[4]), tzinfo=stream_tz)
    et = int(time.mktime(dt.timetuple()))
    return et


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    logger = logging.getLogger(name)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("| %(levelname)s | %(name)s | %(message)s |")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
