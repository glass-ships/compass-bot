import discord
from discord.ext import commands

from compass.config.bot_config import COLORS


class CustomHelpCommand(commands.HelpCommand):
    def __init__(self) -> None:
        super().__init__()

    async def send_bot_help(self, mapping):
        emb = discord.Embed(
            title="Compass Bot Help",
            description="Looking for a commands list?\nNeed help setting up Compass in your server?",
            color=COLORS.random(),
        )
        emb.add_field(name="See the documentation:", value="[Compass docs](https://glass-ships.gitlab.io/compass-bot)")
        emb.set_thumbnail(url="https://gitlab.com/glass-ships/compass-bot/-/raw/main/docs/images/compass.png")
        await self.get_destination().send(embed=emb)

    async def send_cog_help(self, cog):
        return await super().send_cog_help(cog)

    async def send_group_help(self, group):
        return await super().send_group_help(group)

    async def send_command_help(self, command):
        return await super().send_command_help(command)
