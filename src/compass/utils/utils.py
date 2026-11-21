"""Generic utility functions for Compass Bot"""

import logging
import os
import re
import shlex
import subprocess
import time
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import discord
from dateparser import parse as dt_parse
from rich.console import Console

from compass.config.bot_config import COMPASS_ROOT

logger = logging.getLogger(__name__)

console = Console(
    stderr=True,
    style="bright_yellow on black",
)

#############################
### Variables and Classes ###
#############################

REPO_PATH = f"{COMPASS_ROOT.parent}/discord-stuff"
REPO_URL = f"https://oauth2:{os.getenv('GITLAB_PAT')}@gitlab.com/glass-ships/discord-stuff.git"

URL_REGEX = re.compile(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")


class Ddict(dict):
    """dot.notation access to dictionary attributes"""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    # def __len__(self):
    #     return dict.__len__


class URL(str):
    """URL substring checking class

    If URL contains "substring", equality returns True. For example:
        URL("https://www.youtube.com/watch?v=1234567890") == "youtube" => True
    """

    def __eq__(self, other) -> bool:
        return self.__contains__(other)


#####################
### Parsing Utils ###
#####################


def parse_args(arg_str: str) -> Ddict:
    """Parse arguments from a string into a dictionary

    Example:
        >>> parse_args("--title this is a title --description this is a description" --empty)
        {"title": "this is a title", "description": "this is a description", "empty": None}
    """
    args = shlex.split(arg_str)
    opts = {}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--"):
            key = arg.lstrip("-").replace("-", "_")
            # Collect all following arguments until next flag or end
            value_parts: list[str] = []
            i += 1
            while i < len(args) and not args[i].startswith("--"):
                value_parts.append(args[i])
                i += 1
            if len(value_parts) == 0 or (len(value_parts) == 1 and value_parts[0].lower() == "true"):
                opts[key] = True
            elif len(value_parts) == 1 and value_parts[0].lower() == "false":
                opts[key] = False
            elif len(value_parts) == 1 and value_parts[0].lower() == "none":
                opts[key] = None
            else:
                opts[key] = " ".join(value_parts) if value_parts else ""
            # Don't increment i here since we already moved to next flag or end
        else:
            i += 1

    return Ddict(opts)


def extract_url(content: str) -> str | None:
    """Extracts URL from message content, or returns as is"""
    if re.search(URL_REGEX, content):
        result = URL_REGEX.search(content)
        url = result.group(0)  # type: ignore
        if url.startswith("https://m."):
            url = url.replace("https://m.", "https://")
        # logger.info(f"Extracted URL: {url}")
        return url
    return None


##################
### File Utils ###
##################


async def download(
    msg: discord.Message,
    attachment: discord.Attachment,
    path: str | os.PathLike | None,
) -> None:
    """Download an attachment from a message"""
    fp = os.path.join("downloads", msg.guild.name, path or "")
    fn = attachment.filename
    Path(fp).mkdir(parents=True, exist_ok=True)
    await attachment.save(fp=Path(fp) / fn)
    return


def getfilepath(itx, fp) -> str:
    """Returns filepath with guild-specific download path

    Args:
        itx (discord.Message): Message context
        fp (str): File path
    """
    return f"downloads/{itx.guild.name}/{fp}"


#######################
### Date/Time Utils ###
#######################


def parse_date(date_str: str):
    """Parses a time/date-related string into a datetime object."""
    return dt_parse(date_str, settings={"TIMEZONE": "UTC"})


# Timezone abbreviations are fixed UTC offsets (EST is always -5, EDT always -4), so map them
# explicitly rather than relying on dateutil's tz.gettz(), which doesn't recognize most of them.
TZ_OFFSETS = {
    "UTC": 0,
    "GMT": 0,
    "EST": -5,
    "EDT": -4,
    "CST": -6,
    "CDT": -5,
    "MST": -7,
    "MDT": -6,
    "PST": -8,
    "PDT": -7,
    "BST": 1,
    "CET": 1,
    "CEST": 2,
}
TIME_FORMATS = ("%Y-%m-%d %I:%M %p", "%Y-%m-%d %H:%M")  # 12-hour with AM/PM, then 24-hour


def check_time_format(t: str) -> bool:
    """Check that datetime input is in format `YYYY-MM-DD HH:MM [AM/PM] TZ`"""
    pattern = r"\d{4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{2}(\s[aApP][mM])?\s[a-zA-Z]{3,4}"
    return re.fullmatch(pattern, t) is not None


def dt_to_epoch(t: str) -> int:
    """Convert datetime str to epoch time.

    Accepts `YYYY-MM-DD HH:MM AM/PM TZ` (12-hour) or `YYYY-MM-DD HH:MM TZ` (24-hour),
    where TZ is one of the abbreviations in TZ_OFFSETS.

    Raises:
        ValueError: If the time or timezone can't be parsed.
    """
    date_time, tz_abbr = t.strip().rsplit(" ", 1)
    offset = TZ_OFFSETS.get(tz_abbr.upper())
    if offset is None:
        raise ValueError(f"Unknown timezone {tz_abbr!r}; expected one of {', '.join(TZ_OFFSETS)}")
    for fmt in TIME_FORMATS:
        try:
            dt = datetime.strptime(date_time, fmt)
            break
        except ValueError:
            continue
    else:
        raise ValueError(f"Invalid time {date_time!r}; expected 'YYYY-MM-DD HH:MM AM/PM' or 'YYYY-MM-DD HH:MM'")
    return int(dt.replace(tzinfo=timezone(timedelta(hours=offset))).timestamp())


def epoch_to_dt(t):
    """Convert epoch time to datetime"""
    return datetime.fromtimestamp(t)


##################
### Misc Utils ###
##################


def chunk_list(list_to_chunk: list, chunk_size: int) -> Generator[list, None, None]:
    """Yield successive n-sized chunks from list l

    Args:
        list_to_chunk (list): List to chunk into sublists
        chunk_size (int): Size of sublists to subdivide list into

    Yields:
        list: n-sized sublists of list l
    """
    for i in range(0, len(list_to_chunk), chunk_size):
        yield list_to_chunk[i : i + chunk_size]


def get_resource_repo() -> None:
    """Clone or pull resource repo"""
    if not Path(REPO_PATH).exists():
        logger.debug(f"Repo not found - cloning repo to {REPO_PATH}")
        subprocess.call(["git", "clone", REPO_URL, REPO_PATH])
    else:
        logger.debug("Repo already exists - pulling repo")
        subprocess.Popen(["git", "pull"], cwd=REPO_PATH)
        time.sleep(5)


def get_resource_path(guild_name: str, *resource: str) -> str | None:
    """Returns path to resource (checks data repo first, then downloads)

    Args:
        guild_name (str): Name of guild
        resource (str): Resource path (can be nested, e.g. "emojis/png")
    """
    sub_path = "/".join(resource)
    get_resource_repo()
    if os.path.exists(f"{REPO_PATH}/{guild_name}/{sub_path}"):
        resource_path = f"{REPO_PATH}/{guild_name}/{sub_path}"
    elif os.path.exists(f"{COMPASS_ROOT}/downloads/{guild_name}"):
        Path(f"{COMPASS_ROOT}/downloads/{guild_name}/{sub_path}").mkdir(parents=True, exist_ok=True)
        resource_path = f"{COMPASS_ROOT}/downloads/{guild_name}/{sub_path}"
    else:
        return None
    return resource_path
