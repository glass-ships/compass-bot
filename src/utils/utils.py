import os
from pathlib import Path
from typing import Optional, Union

import time, re
from datetime import datetime
from dateutil import tz

URL_REGEX = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

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
    """Normalize a downloaded filepath"""

    return f"downloads/{itx.guild.name}/{fp}"


def check_time_format(t):
    """Check that datetime input is in format YYYY-MM-DD HH:MM AM/PM TZ"""

    pattern = r"\d{4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{2}\s[a-zA-Z]{2}\s[a-zA-Z]{3}"
    match = re.match(pattern, t)
    return bool(match)


def dt_to_epoch(t):
    """Convert datetime to epoch time (format: YYYY-MM-DD HH:MM AM/PM TZ)"""

    msg_split = t.split()
    temp = []
    temp.extend(msg_split[0].split('-'))
    temp.extend(msg_split[1].split(':'))
    temp.append(msg_split[2])
    stream_tz = tz.gettz(msg_split[3])
    dt = datetime(int(temp[0]),int(temp[1]), int(temp[2]), int(temp[3]), int(temp[4]), tzinfo=stream_tz)
    et = int(time.mktime(dt.timetuple()))
    return et

