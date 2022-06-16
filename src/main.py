### Import Libraries  ###

import os

import discord
from discord.ext import commands
#from discord import app_commands
#from discord.utils import get

from classes.music.audiocontroller import AudioController
from classes.music.settings import Settings
from utils.helper import *
from utils.database import *
from utils.music_utils import *

logger = get_logger(__name__)

DEFAULT_PREFIX = ';' 

token = os.getenv("DSC_API_TOKEN")

mongo_url = os.getenv("MONGO_URL")


# Connect to database
async def connect_to_db():
    bot.db = serverDB(mongo_url)
    logger.info("Connected to database.")


# Setup prefix (guild-specific or default)
async def getprefix(bot, ctx):
    if not ctx.guild:
        return commands.when_mentioned_or(DEFAULT_PREFIX)(bot,ctx)
    prefix = bot.db.get_prefix(ctx.guild.id)
    if len(prefix) == 0:
        bot.db.update_prefix(DEFAULT_PREFIX)
        prefix = DEFAULT_PREFIX
    return commands.when_mentioned_or(prefix)(bot,ctx)


# Custom help commands
class CustomHelpCommand(commands.HelpCommand):
    def __init__(self) -> None:
        super().__init__()
    
    async def send_bot_help(self, mapping):
        emb = discord.Embed(
            title="Compass Bot Help",
            description="Looking for a commands list?\nNeed help setting up Compass in your server?"
        )
        emb.add_field(name="See the documentation:", value="[Compass docs](https://glass-ships.gitlab.io/compass-bot)")
        emb.set_thumbnail(url='https://gitlab.com/glass-ships/compass-bot/-/raw/main/docs/images/compass.png')
                
        await self.get_destination().send(embed=emb)
    
    async def send_cog_help(self, cog):
        return await super().send_cog_help(cog)
        output = []
        for cog in mapping:
            cogname = cog.qualified_name if cog else "None"
            if cog:
                cmds = cog.get_commands()
                output.append(f"{cogname}: {[cmd.name for cmd in cmds]}")            
        emb.add_field(name="Cogs", value=[cog.qualified_name for cog in mapping], inline=False)

    async def send_group_help(self, group):
        return await super().send_group_help(group)
    
    async def send_command_help(self, command):
        return await super().send_command_help(command)

async def config_music(guild):

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
                print(e)

        else:
            for vc in vc_channels:
                if vc.id == sett.get('start_voice_channel'):
                    try:
                        await guild_audiocontroller[guild].register_voice_channel(vc_channels[vc_channels.index(vc)])
                    except Exception as e:
                        print(e)

### Setup Discord bot

bot = commands.Bot(
    application_id = 932737557836468297, # main bot
    #application_id = 535346715297841172, # test bot
    help_command=CustomHelpCommand(),
    command_prefix = getprefix,
    description = "A general use and moderation bot in Python.",
    intents = discord.Intents.all()
)


async def startup_tasks():
    logger.info("Connecting to database...")
    await connect_to_db()
    
    print("\nStarting cogs...")
    for f in os.listdir("src/cogs"):
        if f.endswith(".py"):
            await bot.load_extension("cogs." + f[:-3])


@bot.event
async def on_ready():
    for guild in bot.guilds:
        await config_music(guild)
    print(f'\n{bot.user.name} has connected to Discord!')

##########################################################################

# Run bot
logger.info(f"Parent Logger: {logger.parent}")
asyncio.run(startup_tasks())
bot.run(token)
#asyncio.run(bot.tree.sync())
