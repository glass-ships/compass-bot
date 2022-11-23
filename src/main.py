### Import Libraries  ###

import os, sys, getopt

import discord
from discord.ext import commands

from classes.customhelpcommands import CustomHelpCommand
from classes.music.audiocontroller import AudioController
from classes.music.settings import Settings

from utils.utils import *
from utils.database import ServerDB
from utils.music_utils import *
from utils.log_utils import set_log_config, get_logger

# Setup logging
set_log_config()
logger = get_logger("compass.main")

# Parse command line arguments
dev: bool = False
args = sys.argv[1:]
short_options = 'hd'
long_options = ['help', 'dev']
try:
    arguments, values = getopt.getopt(args, short_options, long_options)
except getopt.error as err:
    logger.error(str(err))
    sys.exit(2)

for arg, val in arguments:
    if arg in ("-h", "--help"):
        print("""
Compass Bot
------------
Description: 
    A General use Discord bot with features for moderation, music, Destiny, and more. 

Usage: 
    python src/main.py [-h, --help] [-d, --dev]
    
Optional Arguments:
  -h, --help  Show this help message and exit
  -d, --dev   Run the development version of the Bot locally 
""")
        sys.exit(0)
    elif arg in ('-d', '--dev'):
        dev = True

DEFAULT_PREFIX = ';' 
mongo_url = os.getenv("MONGO_URL")
token = os.getenv("DSC_DEV_TOKEN") if dev else os.getenv("DSC_API_TOKEN")


async def _connect_to_db():
    bot.db = ServerDB(mongo_url, dev=dev)
    logger.info("Connected to database.")

async def _prune_db():
    logger.info("Pruning unused database entries...")

    db_guilds = bot.db.get_all_guilds()
    bot_guilds = [i.id for i in bot.guilds]

    # print(f"Bot guilds: {bot.guilds}")
    # print(f"DB Guilds: {db_guilds}")

    for guild_id in db_guilds:
        if guild_id not in bot_guilds:
            bot.db.drop_guild_table(guild_id)

async def _patch_db():
    logger.info("Patching missing database entries...")

    db_guilds = bot.db.get_all_guilds()
    bot_guilds = [i for i in bot.guilds]

    # print(f"Bot guilds: {bot.guilds}")
    # print(f"DB Guilds: {db_guilds}")

    for guild in bot_guilds:
        default_channel = guild.system_channel.id if guild.system_channel else None
        if guild.id not in db_guilds:
            data = {"guild_id": guild.id, "guild_name": guild.name, "prefix": ";", "mod_roles": [], "mem_role": 0, "dj_role": 0, "chan_bot": default_channel, "chan_logs": default_channel, "chan_music": 0, "chan_vids": 0, "chan_lfg": 0, "videos_whitelist": [], "lfg": []}
            bot.db.add_guild_table(guild.id, data)

async def _get_prefix(bot, ctx):
    """Setup prefix (guild-specific or default)"""
    if not ctx.guild:
        return commands.when_mentioned_or(DEFAULT_PREFIX)(bot,ctx)
    prefix = bot.db.get_prefix(ctx.guild.id)
    if len(prefix) == 0:
        bot.db.update_prefix(DEFAULT_PREFIX)
        prefix = DEFAULT_PREFIX
    return commands.when_mentioned_or(prefix)(bot,ctx)

async def _config_music(guild):
    """Configure music settings for each guild"""
    guild_settings[guild] = Settings(guild)
    guild_audiocontroller[guild] = AudioController(bot, guild)
    sett = guild_settings[guild]

    try:
        await guild.me.edit(nick=sett.get('default_nickname'))
    except:
        pass

    if config.GLOBAL_DISABLE_AUTOJOIN_VC == True:
        return

    vc_channels = guild.voice_channels

    if sett.get('vc_timeout') == False:
        if sett.get('start_voice_channel') == None:
            try:
                await guild_audiocontroller[guild].register_voice_channel(guild.voice_channels[0])
            except Exception as e:
                logger.error(e)

        else:
            for vc in vc_channels:
                if vc.id == sett.get('start_voice_channel'):
                    try:
                        await guild_audiocontroller[guild].register_voice_channel(vc_channels[vc_channels.index(vc)])
                    except Exception as e:
                        logger.error(e)

### Setup Discord bot

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
        await _config_music(guild)
    logger.info(f'{bot.user.name} has connected to Discord!')

##########################################################################

# Run bot
logger.info(f"Parent Logger: {logger.parent}")
asyncio.run(_startup_tasks())
bot.run(token)
#asyncio.run(bot.tree.sync())
