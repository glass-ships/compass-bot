import os, sys, getopt
import asyncio
import discord
from discord.ext import commands

from utils.database import ServerDB
from utils.bot_config import DEFAULT_PREFIX, HELP, default_guild_data

from utils.custom_help_commands import CustomHelpCommand
from music.playback import AudioController
from music.settings import Settings
from music import music_config
from music.music_utils import guild_settings, guild_player

from utils.log_utils import set_log_config, get_logger

set_log_config()
logger = get_logger(f"compass.{__name__}")

####################################
### Parse command line arguments ###
####################################

dev: bool = False
args = sys.argv[1:]
short_options = 'hd'
long_options = ['help', 'dev', 'debug']
try:
    arguments, values = getopt.getopt(args, short_options, long_options)
except getopt.error as err:
    logger.error(str(err))
    sys.exit(2)

for arg, val in arguments:
    if arg in ("-h", "--help"):
        print(HELP)
        sys.exit(0)
    elif arg in ('-d', '--dev'):
        dev = True
    elif arg in ('--debug'):
        set_log_config(10)

mongo_url = os.getenv("MONGO_URL")
token = os.getenv("DSC_DEV_TOKEN") if dev else os.getenv("DSC_API_TOKEN")

###################################
### Connect to/verify database  ###
###################################

async def _connect_to_db():
    """Connects to Mongo database"""

    bot.db = ServerDB(mongo_url, dev=dev)
    logger.info("Connected to database.")


async def _prune_db():
    """Prunes unused database entries"""

    logger.info("Pruning unused database entries...")

    db_guilds = bot.db.get_all_guilds()
    bot_guilds = [i.id for i in bot.guilds]
    logger.debug(f"Bot guilds: {bot.guilds}\nDB Guilds: {db_guilds}")

    for guild_id in db_guilds:
        if guild_id not in bot_guilds:
            logger.debug(f"Bot not in guild with id {guild_id}. Removing database entry.")
            bot.db.drop_guild_table(guild_id)


async def _patch_db():
    """Creates an entry with default values for any guilds missing in database"""

    logger.info("Patching missing database entries...")
    
    db_guilds = bot.db.get_all_guilds()
    bot_guilds = [i for i in bot.guilds]
    logger.debug(f"Bot guilds: {bot.guilds}\nDB Guilds: {db_guilds}")

    for guild in bot_guilds:
        if guild.id not in db_guilds:
            logger.debug(f"Guild: {guild.name} not found in database. Adding default entry.")
            data = default_guild_data(guild)
            bot.db.add_guild_table(guild.id, data)


async def _get_prefix(bot, ctx):
    """Returns a guild's bot prefix, or default if none"""

    if not ctx.guild:
        return commands.when_mentioned_or(DEFAULT_PREFIX)(bot,ctx)
    prefix = bot.db.get_prefix(ctx.guild.id)
    if len(prefix) == 0:
        bot.db.update_prefix(DEFAULT_PREFIX)
        prefix = DEFAULT_PREFIX
    return commands.when_mentioned_or(prefix)(bot,ctx)


async def _set_guild_music_config(guild):
    """Set a guild's music configs"""
    guild_settings[guild] = Settings(guild)
    guild_player[guild] = AudioController(bot, guild)
    sett = guild_settings[guild]

    try:
        await guild.me.edit(nick=sett.get('default_nickname'))
    except:
        pass

    if music_config.GLOBAL_DISABLE_AUTOJOIN_VC == True:
        return

    vc_channels = guild.voice_channels

    if sett.get('vc_timeout') == False:
        if sett.get('start_voice_channel') == None:
            try:
                await guild_player[guild].register_voice_channel(guild.voice_channels[0])
            except Exception as e:
                logger.error(e)

        else:
            for vc in vc_channels:
                if vc.id == sett.get('start_voice_channel'):
                    try:
                        await guild_player[guild].register_voice_channel(vc_channels[vc_channels.index(vc)])
                    except Exception as e:
                        logger.error(e)


############################################
### Define Discord bot and startup tasks ###
############################################

bot = commands.Bot(
    application_id = 535346715297841172 if dev else 932737557836468297,
    help_command=CustomHelpCommand(),
    command_prefix = ',' if dev else _get_prefix,
    pm_help = True,
    description = "A general use, moderation, and music bot in Python.",
    intents = discord.Intents.all()
)


async def _startup_tasks():
    logger.info("Connecting to database...")
    await _connect_to_db()
    
    logger.info("Starting cogs...")
    for f in os.listdir("src/cogs"):
        if f.endswith(".py"):
            await bot.load_extension("cogs." + f[:-3])


@bot.event
async def on_ready():
    await _prune_db()
    await _patch_db()
    for guild in bot.guilds:
        await _set_guild_music_config(guild)
    logger.info(f'{bot.user.name} has connected to Discord!')

###################
### Run the bot ###
###################

if __name__ == "__main__":
    logger.info(f"Top-level Logger: {logger}")
    logger.debug(f"Parent Logger: {logger.parent}")

    asyncio.run(_startup_tasks())
    bot.run(token)

