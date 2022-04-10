#### Import libraries ###

import discord
from discord.utils import get

import time, re, asyncio, json
from datetime import datetime
from dateutil import tz

##### Helper Functions #####

async def role_check(ctx=None, roles=None):
    user_roles = [x.id for x in ctx.author.roles]
    if any(i in user_roles for i in roles):
        return True
    await ctx.send("You do not have permission to use this command.", delete_after=5.0)
    await asyncio.sleep(3)
    await ctx.message.delete()
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

def get_guild(bot, gid):
    guild = bot.get_guild(gid)
    return guild

async def send(guild, channel_id, content = None, embed = None):
    channel = get(guild.text_channels, id=channel_id)
    await channel.send(content=content, embed=embed)
