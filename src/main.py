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

### Define discord bot
#
token = os.getenv("DSC_API_TOKEN")
intents = discord.Intents.all()
description="A general use and moderation bot in Python."
bot = commands.Bot(
    application_id = 932737557836468297, # main bot
    #application_id = 535346715297841172, # test bot
    command_prefix = get_prefix,
    description = description,
    intents = intents
)

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

async def startup_tasks():
    print("Connecting to database...")
    await get_db()
    
    print("Starting cogs...")
    for f in os.listdir("src/cogs"):
        if f.endswith(".py"):
            await bot.load_extension("cogs." + f[:-3])

### Bot configuration commands
#
@bot.command()
@commands.has_permissions(administrator=True)
async def sync(ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Union[None, Literal["~"]] = None):
    if not guilds:
        if spec == "~":
            try:
                fmt = await bot.tree.sync(guild=ctx.guild)
            except discord.HTTPException as e:
                await ctx.send(f"Error syncing commands to current guild:\n```\n{e}\n```")
                return
        else:
            try:
                fmt = await bot.tree.sync()
            except discord.HTTPException as e:
                await ctx.send(f"Error syncing commands globally:\n```\n{e}\n```")
                return

        await ctx.send(
            f"Synced {len(fmt)} commands {'globally' if spec is not None else 'to the current guild.'}"
        )
        return

    assert guilds is not None
    fmt = 0
    for guild in guilds:
        try:
            await bot.tree.sync(guild=guild)
        except discord.HTTPException as e:
            await ctx.send(f"Error syncing commands to guild {guild.id}:\n```\n{e}\n```")
        else:
            fmt += 1

    await ctx.send(f"Synced the tree to {fmt}/{len(guilds)} guilds.")

@bot.tree.command(name="test1")
async def test1(interaction: discord.Interaction):
    """Test slash command 1"""
    response = 'Testing 1!'
    await interaction.response.send_message(response, ephemeral=True)

##########################################################################

asyncio.run(startup_tasks())
bot.run(token)
#asyncio.run(bot.tree.sync())