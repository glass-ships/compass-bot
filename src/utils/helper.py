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
#logger = logging.getLogger(__name__)

url_regex = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

##### Helper Functions #####

async def role_check(ctx=None, roles=None):
    """
    Check if user has required roles
    Usage:
        mod_roles = self.bot.db.get_mod_roles(ctx.guild.id)
        if not await role_check(ctx, mod_roles):
            return
        # rest of your code
    """
    user_roles = [x.id for x in ctx.author.roles]
    if any(i in user_roles for i in roles):
        return True
    await ctx.send("You do not have permission to use this command.", delete_after=5.0)
    await asyncio.sleep(3)
    await ctx.message.delete()
    return False

async def role_check_itx(itx: discord.Interaction=None, roles=None):
    """
    Check if user has required roles (for Interactions)
    Usage:
        mod_roles = self.bot.db.get_mod_roles(itx.guild_id)
        if not await role_check_itx(itx, mod_roles):
            return
        # rest of your code
    """
    user_roles = [x.id for x in itx.user.roles]
    if any(i in user_roles for i in roles):
        return True
    await itx.response.send_message("You do not have permission to use this command.", ephemeral=True)
    return False

##################################################################################

def get_guild(bot, command):
    """
    Gets the guild a command belongs to (for VC commands). 
    Useful, if the command was sent via pm.
    """
    if command.guild is not None:
        return command.guild
    for guild in bot.guilds:
        for channel in guild.voice_channels:
            if command.author in channel.members:
                return guild
    return None

def get_emojis(self, guild):
        emojis = {
            'anim': [],
            'static': []
        }
        for i in guild.emojis:
            if i.animated == True:
                emojis['anim'].append(i.name)
            else:
                emojis['static'].append(i.name)
        return emojis['static'], emojis['anim']

##################################################################################

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

##################################################################################

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

##################################################################################

def get_logger(name: str) -> logging.Logger:
    """Get an instance of logger."""
    logger = logging.getLogger(name)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("|%(levelname)s|%(name)s|%(message)s|")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    #logger.setLevel(logging.DEBUG)
    logger.propagate = False
    return logger