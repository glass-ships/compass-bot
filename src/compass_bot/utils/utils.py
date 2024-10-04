"""Generic utility functions for Compass Bot"""

import os
import re
import subprocess
import time
from collections.abc import Generator
from pathlib import Path
from typing import Optional, Union
from datetime import datetime
from dateutil import tz
from typing import List, Tuple

import discord
import shlex
from loguru import logger
from rich.console import Console

from compass_bot.utils.bot_config import COMPASS_ROOT

console = Console(
    color_system="truecolor",
    stderr=True,
    style="blue1",
)

#############################
### Variables and Classes ###
#############################

REPO_PATH = f"{COMPASS_ROOT.parent}/discord-stuff"
REPO_URL = f"https://glass-ships:{os.getenv('GITLAB_TOKEN')}@gitlab.com/glass-ships/discord-stuff.git"

URL_REGEX = re.compile(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")


class ddict(dict):
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


def parse_args(args: str) -> ddict:
    """Parse arguments from a string into a dictionary"""
    args = shlex.split(args)
    opts = {}
    for i in range(len(args)):
        arg = args[i]
        if arg.startswith("--"):
            opts[arg.lstrip("-").replace("-", "_")] = args[i + 1]
    return ddict(opts)


def extract_url(content: str) -> Optional[str]:
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


def get_emojis(guild: discord.Guild) -> Tuple[List[discord.Emoji], List[discord.Emoji]]:
    """Returns lists of all static and animated emojis in a guild"""

    emojis = {"anim": [], "static": []}
    for i in guild.emojis:
        if i.animated is True:
            emojis["anim"].append(i)
        else:
            emojis["static"].append(i)
    return emojis["static"], emojis["anim"]


async def download(itx, attachment, path: Optional[Union[str, os.PathLike]]) -> None:
    """Download an attachment from a message

    Args:
        itx (discord.Message): Message context
        attachment (discord.Attachment): Attachment to download
        path (Optional[Union[str, os.PathLike]]): Path to save attachment to
    """

    fp = os.path.join("downloads", itx.guild.name, path)
    fn = attachment.filename
    Path(fp).mkdir(parents=True, exist_ok=True)
    await attachment.save(fp=f"{fp}/{fn}")
    return


def getfilepath(itx, fp) -> str:
    """Returns filepath with guild-specific download prefix

    Args:
        itx (discord.Message): Message context
        fp (str): File path
    """
    return f"downloads/{itx.guild.name}/{fp}"


#######################
### Date/Time Utils ###
#######################


def check_time_format(t):
    """Check that datetime input is in format `YYYY-MM-DD HH:MM AM/PM TZ`"""

    pattern = r"\d{4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{2}\s[a-zA-Z]{2}\s[a-zA-Z]{3}"
    match = re.match(pattern, t)
    return bool(match)


def dt_to_epoch(t):
    """Convert datetime to epoch time (requires format: `YYYY-MM-DD HH:MM AM/PM TZ`)"""

    msg_split = t.split()
    temp = []
    temp.extend(msg_split[0].split("-"))
    temp.extend(msg_split[1].split(":"))
    temp.append(msg_split[2])
    stream_tz = tz.gettz(msg_split[3])
    dt = datetime(int(temp[0]), int(temp[1]), int(temp[2]), int(temp[3]), int(temp[4]), tzinfo=stream_tz)
    et = int(time.mktime(dt.timetuple()))
    return et


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
    if not Path(REPO_PATH).is_dir():
        subprocess.call(["git", "clone", REPO_URL, REPO_PATH])
    else:
        logger.debug("Repo already exists - pulling repo")
        subprocess.Popen(["git", "pull"], cwd=REPO_PATH)
        time.sleep(5)


def get_resource_path(guild_name: str, *resource: str) -> Union[str, None]:
    """Returns path to resource

    Args:
        guild_name (str): Name of guild
        resource (str): Resource path (can be nested, e.g. "emojis/png")
    """
    sub_path = "/".join(resource)
    get_resource_repo()
    if os.path.exists(f"{REPO_PATH}/{guild_name}/{sub_path}"):
        resource_path = f"{REPO_PATH}/{guild_name}/{sub_path}"
    elif os.path.exists(f"{COMPASS_ROOT}/downloads/{guild_name}"):
        if not os.path.exists(f"{COMPASS_ROOT}/downloads/{guild_name}/{sub_path}"):
            os.mkdir(f"{COMPASS_ROOT}/downloads/{guild_name}/{sub_path}", parents=True)
        resource_path = f"{COMPASS_ROOT}/downloads/{guild_name}/{sub_path}"
    else:
        return None
    return resource_path
