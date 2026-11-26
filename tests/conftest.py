"""Shared pytest fixtures for Compass Bot.

Discord objects are faked with `unittest.mock`:
- `MagicMock` for plain objects (guilds, members, roles, channels)
- `AsyncMock` for anything the code `await`s (send, defer, add_roles, ...)

The database is a real `ServerDB` backed by `mongomock`, so tests run in memory
with no network access and no MongoDB Atlas connection.
"""

from unittest.mock import AsyncMock, MagicMock

import discord
import mongomock
import pytest

from compass.cogs import utility
from compass.utils import database, utils

GUILD_ID = 1000
MOD_ROLE_ID = 2000

#################
### Downloads ###
#################

# Every module that imports DOWNLOADS_DIR (each import binds its own copy of the name)
DOWNLOADS_DIR_MODULES = [utility, utils]


@pytest.fixture(autouse=True)
def downloads_dir(tmp_path, monkeypatch):
    """Point every DOWNLOADS_DIR at tmp_path, so no test touches the real downloads folder."""
    d = tmp_path / "downloads"
    for mod in DOWNLOADS_DIR_MODULES:
        monkeypatch.setattr(mod, "DOWNLOADS_DIR", d)
    return d


##################
### Database ###
##################


@pytest.fixture
def db(monkeypatch) -> database.ServerDB:
    """In-memory ServerDB (mongomock). Each test gets a fresh, empty database."""
    monkeypatch.setattr(database, "MONGO_URL", "mongodb://mongomock")
    monkeypatch.setattr(database, "MongoClient", mongomock.MongoClient)
    server_db = database.ServerDB(dev=True)
    yield server_db
    server_db.close()


@pytest.fixture
def guild_data() -> dict:
    """A minimal guild document, matching the shape the bot stores."""
    return {
        "guild_id": GUILD_ID,
        "guild_name": "Test Guild",
        "prefix": ";",
        "mod_roles": [MOD_ROLE_ID],
        "mem_role": 0,
        "required_roles": [],
        "chan_bot": 0,
        "chan_logs": 0,
        "chan_music": 0,
        "chan_vids": 0,
        "chan_lfg": 0,
        "chan_welcome": 0,
        "videos_whitelist": [],
    }


@pytest.fixture
def seeded_db(db, guild_data) -> database.ServerDB:
    """ServerDB containing one guild (GUILD_ID) with a mod role (MOD_ROLE_ID)."""
    db.add_guild(GUILD_ID, guild_data)
    return db


###########################
### Fake Discord objects ###
###########################


def make_role(role_id: int, name: str = "role", position: int = 0) -> MagicMock:
    role = MagicMock()
    role.id = role_id
    role.name = name  # NOTE: MagicMock(name=...) names the mock itself, so set .name afterwards
    role.mention = f"<@&{role_id}>"
    # Like discord.Role, roles compare by their position in the role list
    role.position = position
    role.__lt__ = lambda _self, other: role.position < other.position
    role.__gt__ = lambda _self, other: role.position > other.position
    return role


def make_member(user_id: int = 1, name: str = "user", roles=None, admin: bool = False) -> MagicMock:
    member = MagicMock(spec=discord.Member)  # spec: passes isinstance(member, discord.Member)
    member.id = user_id
    member.name = name
    member.display_name = name
    member.mention = f"<@{user_id}>"
    member.roles = list(roles or [])
    member.guild_permissions.administrator = admin
    member.add_roles = AsyncMock()
    member.remove_roles = AsyncMock()
    member.send = AsyncMock()
    return member


@pytest.fixture
def guild() -> MagicMock:
    g = MagicMock()
    g.id = GUILD_ID
    g.name = "Test Guild"
    g.roles = []
    g.emojis = []
    g.filesize_limit = 10 * 1024 * 1024
    return g


@pytest.fixture
def member() -> MagicMock:
    """A regular (non-mod, non-admin) member."""
    return make_member(user_id=1, name="regular")


@pytest.fixture
def mod_member() -> MagicMock:
    """A member holding the guild's mod role."""
    return make_member(user_id=2, name="moderator", roles=[make_role(MOD_ROLE_ID, "Mod")])


@pytest.fixture
def itx(guild, member, bot) -> MagicMock:
    """Fake `discord.Interaction` for slash commands.

    Assert on: itx.response.defer, itx.response.send_message, itx.followup.send, itx.channel.send
    """
    i = MagicMock()
    i.guild = guild
    i.guild_id = guild.id
    i.client = bot
    i.user = member
    i.response.defer = AsyncMock()
    i.response.send_message = AsyncMock()
    i.response.is_done = MagicMock(return_value=False)
    i.followup.send = AsyncMock()
    i.channel.send = AsyncMock()
    i.channel.id = 3000
    return i


@pytest.fixture
def ctx(guild, member, bot) -> MagicMock:
    """Fake `commands.Context` for prefix (text) commands.

    Assert on: ctx.send, ctx.reply, ctx.message.delete
    """
    c = MagicMock()
    c.guild = guild
    c.author = member
    c.bot = bot
    c.send = AsyncMock()
    c.reply = AsyncMock()
    c.message.delete = AsyncMock()
    c.channel.send = AsyncMock()
    return c


@pytest.fixture
def bot(seeded_db) -> MagicMock:
    """Fake CompassBot whose `.db` is the seeded in-memory ServerDB."""
    b = MagicMock()
    b.db = seeded_db
    b.latency = 0.05
    return b
