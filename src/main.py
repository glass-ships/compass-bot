### Import Libraries  ###

import os
from typing import Union, List, Optional, Literal

import discord
from discord.ext import commands
from discord import app_commands
from discord.utils import get

from helper import *
from database import *

##########################################################################

### Connect to database
#
mongo_url = os.getenv("MONGO_URL")
async def get_db():
    bot.db = serverDB(mongo_url)
    print("Connected to database")

### Setup prefix (guild-specific or default)
#
DEFAULT_PREFIX = ';' 
async def get_prefix(bot, ctx):
    if not ctx.guild:
        return commands.when_mentioned_or(DEFAULT_PREFIX)(bot,ctx)
    prefix = bot.db.get_prefix(ctx.guild.id)
    if len(prefix) == 0:
        bot.db.update_prefix(DEFAULT_PREFIX)
        prefix = DEFAULT_PREFIX
    return commands.when_mentioned_or(prefix)(bot,ctx)

### Custom help commands
#
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
        # output = []
        # for cog in mapping:
        #     cogname = cog.qualified_name if cog else "None"
        #     if cog:
        #         cmds = cog.get_commands()
        #         output.append(f"{cogname}: {[cmd.name for cmd in cmds]}")            
        
        await self.get_destination().send(embed=emb)
    
    async def send_cog_help(self, cog):
        return await super().send_cog_help(cog)

    async def send_group_help(self, group):
        return await super().send_group_help(group)
    
    async def send_command_help(self, command):
        return await super().send_command_help(command)

### Define discord bot
#
token = os.getenv("DSC_API_TOKEN")
bot = commands.Bot(
    application_id = 932737557836468297, # main bot
    #application_id = 535346715297841172, # test bot
    help_command=CustomHelpCommand(),
    command_prefix = get_prefix,
    description = "A general use and moderation bot in Python.",
    intents = discord.Intents.all()
)

async def startup_tasks():
    print("\nConnecting to database...")
    await get_db()
    
    print("\nStarting cogs...")
    for f in os.listdir("src/cogs"):
        if f.endswith(".py"):
            await bot.load_extension("cogs." + f[:-3])

@bot.event
async def on_ready():
    print(f'\n{bot.user.name} has connected to Discord!')

##########################################################################

asyncio.run(startup_tasks())
bot.run(token)
#asyncio.run(bot.tree.sync())