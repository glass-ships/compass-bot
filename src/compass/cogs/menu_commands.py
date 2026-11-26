import logging

import discord
from discord import app_commands
from discord.ext import commands

from compass.bot import CompassBot
from compass.utils.checks import has_mod_itx
from compass.utils.command_utils import move_message

logger = logging.getLogger(__name__)


bot: CompassBot  # set in the cog's __init__ via `global bot`


async def setup(bot):
    """Cog setup method"""
    await bot.add_cog(MenuCommands(bot))


class SelectMenuChannel(discord.ui.ChannelSelect):
    """Discord's native channel picker: searchable, with no 25-option limit (a hand-built Select is capped at 25)."""

    def __init__(self, message_id: int) -> None:
        self.message_id = message_id
        super().__init__(
            placeholder="Select a channel",
            channel_types=[
                discord.ChannelType.text,
                discord.ChannelType.news,
                discord.ChannelType.public_thread,
                discord.ChannelType.private_thread,
            ],
        )

    async def callback(self, itx: discord.Interaction) -> None:
        channel = itx.guild.get_channel_or_thread(self.values[0].id)  # values are partial channels; resolve them
        if channel is None:  # e.g. deleted while the picker was open
            await itx.response.send_message("Channel not found.", ephemeral=True)
            return
        try:
            await move_message(itx, channel, str(self.message_id))
        except Exception as e:
            await itx.followup.send(f"An error occurred while moving the message: {e}", ephemeral=True)
            raise


class MenuCommands(commands.Cog):
    def __init__(self, bot_: CompassBot) -> None:
        global bot
        bot = bot_
        self.ctx_menu = app_commands.ContextMenu(name="Move Message", callback=self._move_message)
        bot.tree.add_command(self.ctx_menu)

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")

    async def cog_unload(self) -> None:
        bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    @has_mod_itx
    async def _move_message(self, itx: discord.Interaction, msg: discord.Message) -> None:
        """Right-click > Apps > Move Message: pick a channel to move the message to."""
        await itx.response.defer(ephemeral=True)
        view = discord.ui.View()
        view.add_item(SelectMenuChannel(message_id=msg.id))
        await itx.followup.send("Select a channel to move the message to:", view=view)
