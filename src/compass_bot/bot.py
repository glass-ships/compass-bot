import argparse
import asyncio
import logging
import os
import sys
from typing import Union

import discord
from discord.ext import commands

from compass_bot.music.music_utils import guild_player
from compass_bot.music.player import MusicPlayer
from compass_bot.utils.bot_config import DEFAULT_PREFIX, MODULES, GuildData
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
    logging.INFO if args.log_level == logging.DEBUG else logging.CRITICAL if args.quiet else logging.WARNING
)
discord.utils.setup_logging(level=logging.WARNING)  # discord_log_level)
DISCORD_TOKEN = os.getenv("DSC_DEV_TOKEN") if args.dev else os.getenv("DSC_API_TOKEN")
assert DISCORD_TOKEN is not None, (
    "No Discord API token found. Please set the DSC_API_TOKEN or DSC_DEV_TOKEN environment variable."
)

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
    def __init__(self, dev: bool = False):
        """Initialize the bot"""
        self.app_id = 535346715297841172 if dev else 932737557836468297
        self.prefix = "," if dev else self._get_prefix
        self.bot = create_bot(self.app_id, self.prefix)
        self.bot.add_listener(self.on_ready)
        self.bot.db = None

    async def on_ready(self):
        """Tasks to run when bot is ready"""
        await self._prune_db()
        await self._patch_db()
        for guild in self.bot.guilds:
            # logger.info(f"Setting music config for guild: {guild.name}")
            # await self._set_guild_music_config(guild)
            guild_player[guild] = MusicPlayer(self.bot, guild)
        logger.info(f"{self.bot.user} is online.")

    async def startup_tasks(self, dev):
        """Tasks to run on bot startup"""
        ## Connect to database
        logger.info("Connecting to database...")
        await self._connect_to_db(dev)

        ## Load cogs
        logger.info("Loading cogs...")
        for cog in MODULES:
            await self.bot.load_extension(f"cogs.{cog}")

    ### Database Methods

    async def _connect_to_db(self, dev: bool = False):
        """Connects to database"""
        try:
            self.bot.db = ServerDB(dev=dev)
            logger.info("Connected to database.")
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
        return

    async def _prune_db(self):
        """Prunes unused database entries"""
        logger.info("Pruning unused database entries...")
        db_guilds = self.bot.db.get_all_guilds()
        bot_guilds = [i.id for i in self.bot.guilds]
        logger.debug(f"Bot guilds: {[(g.name, g.id) for g in self.bot.guilds]}")
        logger.debug(f"DB Guilds: {db_guilds}")
        for guild_id in db_guilds:
            if guild_id not in bot_guilds:
                logger.debug(f"Bot not in guild with id {guild_id}. Removing database entry.")
                result = self.bot.db.drop_guild_table(guild_id)
                if result:
                    logger.debug(f"Database entry for guild {guild_id} removed.")
                else:
                    logger.error(f"Error removing database entry for guild {guild_id}.")
        return

    async def _patch_db(self):
        """Creates an entry with default values for any guilds missing in database"""

        logger.info("Patching missing database entries...")

        db_guilds = self.bot.db.get_all_guilds()
        bot_guilds = [i for i in self.bot.guilds]
        logger.debug(f"Bot guilds: {[(g.name, g.id) for g in self.bot.guilds]}")
        logger.debug(f"DB Guilds: {db_guilds}")
        for guild in bot_guilds:
            if guild.id not in db_guilds:
                logger.debug(f"Guild: {guild.name} not found in database. Adding default entry.")
                data = GuildData(guild).__dict__
                del data["guild"]
                result = self.bot.db.add_guild(guild.id, data)
                if result:
                    logger.debug(f"Database entry for guild {guild.id} added.")
                else:
                    logger.error(f"Error adding database entry for guild {guild.id}.")
        return

    ### Misc

    async def _get_prefix(self, bot, ctx) -> Union[str, list[str]]:
        """Returns a guild's bot prefix, or default if none"""
        if not ctx.guild:
            return commands.when_mentioned_or(DEFAULT_PREFIX)(bot, ctx)
        prefix = self.bot.db.get_prefix(ctx.guild.id)
        if len(prefix) == 0:
            self.bot.db.update_prefix(DEFAULT_PREFIX)
            prefix = DEFAULT_PREFIX
        return commands.when_mentioned_or(prefix)(bot, ctx)

    ### Shutdown

    async def shutdown(self):
        """Gracefully shuts down the bot"""
        self.bot.loop.stop()
        await self.bot.close()
        logger.info(f"{self.bot.user.name} offline.")  # type: ignore
        sys.exit(0)


###################
### Run the bot ###
###################

compass = CompassBot(dev=args.dev)
asyncio.run(compass.startup_tasks(args.dev))
try:
    asyncio.run(compass.bot.start(DISCORD_TOKEN))
except KeyboardInterrupt:
    asyncio.run(compass.shutdown())
