import argparse
import os
import sys
from pathlib import Path

import asyncio
import discord
from discord.ext import commands

from compass_bot.utils.bot_config import GuildData, DEFAULT_PREFIX, COMPASS_SRC
from compass_bot.utils.custom_help_commands import CustomHelpCommand
from compass_bot.utils.db_utils import ServerDB
from compass_bot.utils.log_utils import get_logger


#######################
### Parse Arguments ###
#######################

parser = argparse.ArgumentParser(prog="Compass Bot", description="A Discord bot in Python")
parser.add_argument("--dev", action="store_true")
parser.add_argument("--update", action="store_true")
parser.add_argument("--log-level", "-l", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
parser.add_argument("--quiet", "-q", action="store_true")
args = parser.parse_args()

### Setup logging and fetch Discord API token

logger = get_logger(name="compass", level=args.log_level)
discord_log_level = (
    "INFO"
    if args.log_level == "DEBUG"
    else "CRITICAL"
    if args.quiet
    else "WARNING"
    # "DEBUG" if args.log_level == "DEBUG" else "CRITICAL" if args.log_level == "CRITICAL" else "INFO"
)
discord.utils.setup_logging(level="WARNING")#discord_log_level)
DISCORD_TOKEN = os.getenv("DSC_DEV_TOKEN") if args.dev else os.getenv("DSC_API_TOKEN")

##################
### Define Bot ###
##################


def create_bot(id, prefix) -> commands.Bot:
    bot = commands.Bot(
        application_id=id,
        command_prefix=prefix,
        help_command=CustomHelpCommand(),
        pm_help=True,
        description="A general use, moderation, and music bot in Python.",
        intents=discord.Intents.all(),
    )
    return bot


class CompassBot:
    def __init__(self, logger, dev: bool = False):
        self.app_id = 535346715297841172 if dev else 932737557836468297
        self.prefix = "," if dev else self.get_prefix
        self.bot = create_bot(self.app_id, self.prefix)
        self.bot.add_listener(self.on_ready)
        self.bot.logger = logger

    async def on_ready(self):
        await self.prune_db()
        await self.patch_db()
        for guild in self.bot.guilds:
            await self.set_guild_music_config(guild)
        self.bot.logger.info(f"{self.bot.user} is online.")

    async def startup_tasks(self, dev):
        self.bot.logger.info("Connecting to database...")
        await self.connect_to_db(dev)

        self.bot.logger.info("Loading cogs...")
        for f in Path(COMPASS_SRC / "cogs").glob("*.py"):
            # print(f)
            await self.bot.load_extension(f"cogs.{f.stem}")

    async def get_prefix(self, bot, ctx):
        """Returns a guild's bot prefix, or default if none"""

        if not ctx.guild:
            return commands.when_mentioned_or(DEFAULT_PREFIX)(bot, ctx)
        prefix = self.bot.db.get_prefix(ctx.guild.id)
        if len(prefix) == 0:
            self.bot.db.update_prefix(DEFAULT_PREFIX)
            prefix = DEFAULT_PREFIX
        return commands.when_mentioned_or(prefix)(bot, ctx)

    async def set_guild_music_config(self, guild_id):
        """Set a guild's music configs"""

        from compass_bot.music.player import MusicPlayer
        from compass_bot.music.music_utils import guild_player

        guild_player[guild_id] = MusicPlayer(self.bot, guild_id)
        return

    ### Database Methods

    async def connect_to_db(self, dev: bool = False):
        """Connects to Mongo database"""

        mongo_url = os.getenv("MONGO_URL")
        try:
            self.bot.db = ServerDB(mongo_url, dev=dev)
            self.bot.logger.info("Connected to database.")
        except Exception as e:
            self.bot.logger.error(f"Error connecting to database: {e}")
        return

    async def prune_db(self):
        """Prunes unused database entries"""

        self.bot.logger.info("Pruning unused database entries...")

        db_guilds = self.bot.db.get_all_guilds()
        bot_guilds = [i.id for i in self.bot.guilds]
        self.bot.logger.debug(f"Bot guilds: {self.bot.guilds}\nDB Guilds: {db_guilds}")

        for guild_id in db_guilds:
            if guild_id not in bot_guilds:
                self.bot.logger.debug(f"Bot not in guild with id {guild_id}. Removing database entry.")
                self.bot.db.drop_guild_table(guild_id)
        return

    async def patch_db(self):
        """Creates an entry with default values for any guilds missing in database"""

        self.bot.logger.info("Patching missing database entries...")

        db_guilds = self.bot.db.get_all_guilds()
        bot_guilds = [i for i in self.bot.guilds]
        self.bot.logger.debug(f"Bot guilds: {self.bot.guilds}\nDB Guilds: {db_guilds}")

        for guild in bot_guilds:
            if guild.id not in db_guilds:
                self.bot.logger.debug(f"Guild: {guild.name} not found in database. Adding default entry.")
                data = GuildData(guild).__dict__
                del data["guild"]
                self.bot.db.add_guild_table(guild.id, data)
        return

    async def shutdown(self):
        """Gracefully shuts down the bot"""
        self.bot.loop.stop()
        # self.bot.loop.close()
        await self.bot.close()
        self.bot.logger.info(f"{self.bot.user.name} offline.")  # type: ignore
        sys.exit(0)


###################
### Run the bot ###
###################

compass = CompassBot(logger=logger, dev=args.dev)
asyncio.run(compass.startup_tasks(args.dev))
try:
    asyncio.run(compass.bot.start(DISCORD_TOKEN))
except KeyboardInterrupt:
    asyncio.run(compass.shutdown())
