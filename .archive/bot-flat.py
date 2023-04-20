import argparse
import os
import sys

import asyncio
import discord
from discord.ext import commands
# import loguru

from compass_bot.music.player import MusicPlayer
from compass_bot.music.music_utils import guild_player
from compass_bot.utils.bot_config import DEFAULT_PREFIX, HELP, GuildData
from compass_bot.utils.custom_help_commands import CustomHelpCommand
from compass_bot.utils.database import ServerDB
from compass_bot.utils.log_utils import get_logger
from compass_bot.utils.utils import console


#######################
### Parse Arguments ###
#######################

parser = argparse.ArgumentParser(prog='Compass Bot', description='A Discord bot in Python')
parser.add_argument("--dev", action="store_true")
parser.add_argument("--update", action="store_true")
parser.add_argument('--verbose', action='store_true')
parser.add_argument('--quiet', action='store_true')
args = parser.parse_args()

### Setup logging and fetch Discord API token

# discord.utils.setup_logging(level = "DEBUG" if args.verbose else "WARNING" if args.quiet else "INFO")
discord.utils.setup_logging(level = "INFO")

logger = get_logger(name="compass", verbose = True if args.verbose else False if args.quiet else None)

DISCORD_TOKEN = os.getenv("DSC_DEV_TOKEN") if args.dev else os.getenv("DSC_API_TOKEN")

####################################
### Startup Tasks ###
####################################

bot = commands.Bot(
        application_id = 535346715297841172 if args.dev else 932737557836468297,
        help_command=CustomHelpCommand(),
        command_prefix = ',' if args.dev else get_prefix,
        pm_help = True,
        description = "A general use, moderation, and music bot in Python.",
        intents = discord.Intents.all()
)

@bot.event
async def on_ready(self):
    await prune_db()
    await patch_db()
    for guild in bot.guilds:
        await set_guild_music_config(guild)
    logger.info(f'{bot.user} is online.')
    logger.info("Loading cogs...")
    for f in os.listdir("src/compass_bot/cogs"):
        print(f)
        if f.endswith(".py"):                
            await bot.load_extension(f"cogs.{f[:-3]}")
        
async def startup_tasks(dev):
    """  """
    logger.info("Connecting to database...")
    await connect_to_db(dev)
    
    logger.info("Loading cogs...")
    for f in os.listdir("src/compass_bot/cogs"):
        print(f)
        if f.endswith(".py"):                
            await bot.load_extension(f"cogs.{f[:-3]}")

async def get_prefix(bot, ctx):
    """Returns a guild's bot prefix, or default if none"""

    if not ctx.guild:
        return commands.when_mentioned_or(DEFAULT_PREFIX)(bot,ctx)
    prefix = db.get_prefix(ctx.guild.id)
    if len(prefix) == 0:
        db.update_prefix(DEFAULT_PREFIX)
        prefix = DEFAULT_PREFIX
    return commands.when_mentioned_or(prefix)(bot,ctx)

async def set_guild_music_config(guild_id) -> None:
    """Set a guild's music configs"""

    guild_player[guild_id] = MusicPlayer(guild_id)
    return

########################
### Database Methods ###
########################

async def connect_to_db(dev: bool = False):
    """Connects to Mongo database"""

    mongo_url = os.getenv("MONGO_URL")
    try:
        db = ServerDB(mongo_url, dev=dev)
        logger.info("Connected to database.")
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
    return

async def prune_db(self):
    """Prunes unused database entries"""

    logger.info("Pruning unused database entries...")

    db_guilds = db.get_all_guilds()
    bot_guilds = [i.id for i in guilds]
    logger.debug(f"Bot guilds: {guilds}\nDB Guilds: {db_guilds}")

    for guild_id in db_guilds:
        if guild_id not in bot_guilds:
            logger.debug(f"Bot not in guild with id {guild_id}. Removing database entry.")
            db.drop_guild_table(guild_id)
    return

async def patch_db(self):
    """Creates an entry with default values for any guilds missing in database"""

    logger.info("Patching missing database entries...")
    
    db_guilds = db.get_all_guilds()
    bot_guilds = [i for i in guilds]
    logger.debug(f"Bot guilds: {guilds}\nDB Guilds: {db_guilds}")

    for guild in bot_guilds:
        if guild.id not in db_guilds:
            logger.debug(f"Guild: {guild.name} not found in database. Adding default entry.")
            data = GuildData(guild).__dict__
            del data['guild']
            db.add_guild_table(guild.id, data)
    return



async def shutdown(self):
    await compass.bot.close()
    logger.info(f'{bot.user.name} offline.')
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
