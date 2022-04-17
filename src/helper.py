#### Import libraries ###

import discord
from discord.utils import get

import os
from pathlib import Path
from typing import Optional, Union

import time, re, asyncio
from datetime import datetime
from dateutil import tz


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

# Assert datetime format
def check_time_format(t):
    pattern = r"\d{4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{2}\s[a-zA-Z]{2}\s[a-zA-Z]{3}"
    match = re.match(pattern, t)
    check = bool(match)
    return check

# Convert datetime to epoch time (assumes format "YYYY-MM-DD HH:MM AM/PM TZ")
def dt_to_epoch(t):
    msg_split = t.split()
    temp = []
    temp.extend(msg_split[0].split('-'))
    temp.extend(msg_split[1].split(':'))
    temp.append(msg_split[2])
    stream_tz = tz.gettz(msg_split[3])
    dt = datetime(int(temp[0]),int(temp[1]), int(temp[2]), int(temp[3]), int(temp[4]), tzinfo=stream_tz)
    et = int(time.mktime(dt.timetuple()))
    return et

# Download attachment from a message
async def download(itx, attachment, path: Optional[Union[str, os.PathLike]]) -> None:
    fp = os.path.join("downloads", itx.guild.name, path)
    fn = attachment.filename
    Path(fp).mkdir(parents=True, exist_ok=True)
    await attachment.save(fp=f"{fp}/{fn}")
    return

# Normalize a downloaded filepath
def getfile(itx, fp) -> str:
    return f"downloads/{itx.guild.name}/{fp}"