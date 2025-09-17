import argparse
import asyncio
import logging
import os
import sys
from typing import Union

import discord
from discord.ext import commands

from compass.music.music_utils import guild_player
from compass.music.player import MusicPlayer
from compass.config.bot_config import DEFAULT_PREFIX, MODULES, GuildData
from compass.utils.custom_help_commands import CustomHelpCommand
from compass.utils.db_utils import ServerDB
from compass.utils.log_utils import get_logger

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
discord.utils.setup_logging(
    level=logging.WARNING
    # logging.INFO if args.log_level == logging.DEBUG else logging.CRITICAL if args.quiet else logging.WARNING
)
DISCORD_TOKEN = os.getenv("DSC_DEV_TOKEN") if args.dev else os.getenv("DSC_API_TOKEN")
assert DISCORD_TOKEN is not None, (
    "No Discord API token found. Please set the DSC_API_TOKEN or DSC_DEV_TOKEN environment variable."
)

##################
### Define Bot ###
##################


class CompassBot(commands.Bot):
    def __init__(self, dev: bool, *args, **kwargs):
        prefix = "," if dev else self._get_prefix
        super().__init__(command_prefix=prefix, *args, **kwargs)
        # self.add_listener(self.on_ready)

    async def on_ready(self):
        """Tasks to run when bot is ready"""
        await self.wait_until_ready()
        # Patch/prune database entries
        await self._prune_db()
        await self._patch_db()

        # Setup guild music players
        for guild in self.guilds:
            logger.debug(f"Setting music config for guild: {guild.name}")
            guild_player[guild] = MusicPlayer(self, guild)

        logger.info(f"{self.user} is online.")

    async def startup_tasks(self, dev):
        """Tasks to run on bot startup"""
        # Connect to database
        logger.info("Connecting to database...")
        await self._connect_to_db(dev)

        # Load cogs
        logger.info("Loading cogs...")
        for cog in MODULES:
            await self.load_extension(f"cogs.{cog}")

    ### Database Methods

    async def _connect_to_db(self, dev: bool = False):
        """Connects to database"""
        try:
            self.db = ServerDB(dev=dev)
            logger.info("Connected to database.")
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
        return

    async def _prune_db(self):
        """Prunes unused database entries"""
        logger.info("Pruning unused database entries...")
        db_guilds = self.db.get_all_guilds()
        bot_guilds = [i.id for i in self.guilds]
        logger.debug(f"Bot guilds: {[(g.name, g.id) for g in self.guilds]}")
        logger.debug(f"DB Guilds: {db_guilds}")
        for guild_id in db_guilds:
            if guild_id not in bot_guilds:
                logger.debug(f"Bot not in guild with id {guild_id}. Removing database entry.")
                result = self.db.drop_guild_table(guild_id)
                if result:
                    logger.debug(f"Database entry for guild {guild_id} removed.")
                else:
                    logger.error(f"Error removing database entry for guild {guild_id}.")
        return

    async def _patch_db(self):
        """Creates an entry with default values for any guilds missing in database"""

        logger.info("Patching missing database entries...")

        db_guilds = self.db.get_all_guilds()
        bot_guilds = [i for i in self.guilds]
        logger.debug(f"Bot guilds: {[(g.name, g.id) for g in self.guilds]}")
        logger.debug(f"DB Guilds: {db_guilds}")
        for guild in bot_guilds:
            if guild.id not in db_guilds:
                logger.debug(f"Guild: {guild.name} not found in database. Adding default entry.")
                data = GuildData(guild).__dict__
                del data["guild"]
                result = self.db.add_guild(guild.id, data)
                if result:
                    logger.debug(f"Database entry for guild {guild.id} added.")
                else:
                    logger.error(f"Error adding database entry for guild {guild.id}.")
        return

    ### Misc
    async def _get_prefix(self, bot: "CompassBot", msg: discord.Message) -> Union[str, list[str]]:
        """Returns a guild's self prefix, or default if none"""
        logging.debug(f"Locals: {locals()}")
        logging.debug(f"Getting prefix for {msg.guild.name}")
        if not msg.guild:
            return commands.when_mentioned_or(DEFAULT_PREFIX)(bot, msg)
        prefix = self.db.get_prefix(msg.guild.id)
        logging.debug(f"Prefix found: {prefix}")
        if prefix is None or len(prefix) == 0:
            logging.debug(f"Setting default prefix for {msg.guild.name}")
            self.db.update_prefix(msg.guild.id, DEFAULT_PREFIX)
            prefix = DEFAULT_PREFIX
        logging.debug(f"Using prefix {prefix} for {msg.guild.name}")
        return commands.when_mentioned_or(prefix)(bot, msg)

    ### Shutdown

    async def shutdown(self):
        """Gracefully shuts down the bot"""
        self.loop.stop()
        await self.close()
        logger.info(f"{self.user.name} offline.")  # type: ignore
        sys.exit(0)


###################
### Run the bot ###
###################

if __name__ == "__main__":
    compass = CompassBot(
        dev=args.dev,
        application_id=535346715297841172 if args.dev else 932737557836468297,
        help_command=CustomHelpCommand(),
        pm_help=True,
        description="A general use, moderation, and music bot in Python.",
        intents=discord.Intents.all(),
    )
    asyncio.run(compass.startup_tasks(args.dev))
    try:
        asyncio.run(compass.start(DISCORD_TOKEN))
    except KeyboardInterrupt:
        asyncio.run(compass.shutdown())
