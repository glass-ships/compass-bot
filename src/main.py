import os, sys
import getopt
import signal

import asyncio
import discord
from discord.ext import commands

from utils.database import ServerDB
from utils.bot_config import DEFAULT_PREFIX, HELP, default_guild_data

from utils.custom_help_commands import CustomHelpCommand
from utils.log_utils import get_logger
# from utils.logutils import setup_logging

dev: bool = False
verbose: bool = None
try:
    arguments, values = getopt.getopt(
            args=sys.argv[1:], 
            shortopts=None,
            longopts=['help', 'dev', 'debug']
            )
except getopt.error as err:
    print(str(err))
    sys.exit(2)

for arg, val in arguments:
    match arg:
        case "--help":
            print(HELP)
            sys.exit(0)
        case "--dev":
            dev = True
        case "--debug":
            verbose = True

logger = get_logger(f"compass", verbose)
discord.utils.setup_logging()

############################################
### Define Bot and Startup Tasks ###
############################################

class CompassBot:

    def __init__(self, dev: bool = False) -> None:

        # global bot
        self.bot = commands.Bot(
                application_id = 535346715297841172 if dev else 932737557836468297,
                help_command=CustomHelpCommand(),
                command_prefix = ',' if dev else self.get_prefix,
                pm_help = True,
                description = "A general use, moderation, and music bot in Python.",
                intents = discord.Intents.all()
                )
        
        @self.bot.event
        async def on_ready():
            await self.prune_db()
            await self.patch_db()
            for guild in self.bot.guilds:
                await self.set_guild_music_config(guild)
            logger.info(f'{self.bot.user.name} is online.')
           
    async def startup_tasks(self):
        """"""
        logger.info("Connecting to database...")
        await self.connect_to_db()
        
        logger.info("Loading cogs...")
        for f in os.listdir("src/cogs"):
            if f.endswith(".py"):
                await self.bot.load_extension(f"cogs.{f[:-3]}")
                
    async def connect_to_db(self, dev: bool = False):
        """Connects to Mongo database"""

        mongo_url = os.getenv("MONGO_URL")
        try:
            self.bot.db = ServerDB(mongo_url, dev=dev)
            logger.info("Connected to database.")
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
        return

    async def prune_db(self):
        """Prunes unused database entries"""

        logger.info("Pruning unused database entries...")

        db_guilds = self.bot.db.get_all_guilds()
        bot_guilds = [i.id for i in self.bot.guilds]
        logger.debug(f"Bot guilds: {self.bot.guilds}\nDB Guilds: {db_guilds}")

        for guild_id in db_guilds:
            if guild_id not in bot_guilds:
                logger.debug(f"Bot not in guild with id {guild_id}. Removing database entry.")
                self.bot.db.drop_guild_table(guild_id)
        return

    async def patch_db(self):
        """Creates an entry with default values for any guilds missing in database"""

        logger.info("Patching missing database entries...")
        
        db_guilds = self.bot.db.get_all_guilds()
        bot_guilds = [i for i in self.bot.guilds]
        logger.debug(f"Bot guilds: {self.bot.guilds}\nDB Guilds: {db_guilds}")

        for guild in bot_guilds:
            if guild.id not in db_guilds:
                logger.debug(f"Guild: {guild.name} not found in database. Adding default entry.")
                data = default_guild_data(guild)
                self.bot.db.add_guild_table(guild.id, data)
        return

    async def get_prefix(self, bot, ctx):
        """Returns a guild's bot prefix, or default if none"""

        if not ctx.guild:
            return commands.when_mentioned_or(DEFAULT_PREFIX)(bot,ctx)
        prefix = self.bot.db.get_prefix(ctx.guild.id)
        if len(prefix) == 0:
            self.bot.db.update_prefix(DEFAULT_PREFIX)
            prefix = DEFAULT_PREFIX
        return commands.when_mentioned_or(prefix)(bot,ctx)

    async def set_guild_music_config(self, guild):
        """Set a guild's music configs"""
        from music.settings import Settings
        from music.playback import MusicPlayer
        from music.music_utils import guild_settings, guild_player

        guild_settings[guild] = Settings(guild)
        guild_player[guild] = MusicPlayer(self.bot, guild)
        sett = guild_settings[guild]

        try:
            await guild.me.edit(nick=sett.get('default_nickname'))
        except:
            pass

        return

    async def shutdown(self):
        await compass.bot.close()
        logger.info(f'{self.bot.user.name} offline.')
        sys.exit(0)

##############################################################################
### Run the bot

logger.debug(f"Top-level Logger: {logger}")
logger.debug(f"Parent Logger: {logger.parent}")

token = os.getenv("DSC_DEV_TOKEN") if dev else os.getenv("DSC_API_TOKEN")

compass = CompassBot(dev=dev)
asyncio.run(compass.startup_tasks())

try:
    asyncio.run(compass.bot.start(token))
except KeyboardInterrupt:
    asyncio.run(compass.shutdown())
