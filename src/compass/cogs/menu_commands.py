from typing import List

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from compass.bot import CompassBot
from compass.utils.command_utils import move_message


async def mod_check_itx(itx: discord.Interaction):
    mod_roles = bot.db.get_mod_roles(itx.guild_id)
    user_roles = [x.id for x in itx.user.roles]
    if itx.user.guild_permissions.administrator:
        return True
    if any(int(i) in user_roles for i in mod_roles):
        return True
    await itx.response.send_message("You do not have permission to use this command.", ephemeral=True)
    return False


has_mod_itx = app_commands.check(mod_check_itx)


async def setup(bot):
    """Cog setup method"""
    await bot.add_cog(MenuCommands(bot))


class SelectMenuChannel(discord.ui.Select):
    def __init__(
        self,
        options: List[discord.SelectOption],
        message_id: int,
    ) -> None:
        self.message_id = message_id
        super().__init__(
            custom_id="Select a Channel ",
            options=options,
        )

    async def callback(self, itx: discord.Interaction) -> None:
        if itx.guild is not None:
            if channel := itx.guild.get_channel(int(self.values[0])):
                try:
                    await move_message(itx, channel, str(self.message_id))
                except Exception as e:
                    await itx.followup.send(f"An error occurred while moving the message: {e}", ephemeral=True)
                    raise e
            else:
                await itx.followup.send("Channel not found.", ephemeral=True)
                return


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
    async def _move_message(self, itx: discord.Interaction, message: discord.Message) -> None:
        """Command description."""
        await itx.response.defer(ephemeral=True)
        channels = [
            discord.SelectOption(
                label=channel.name, value=str(channel.id), description=channel.topic, emoji=None, default=False
            )
            for channel in message.guild.text_channels
        ]
        view = discord.ui.View()
        view.add_item(SelectMenuChannel(options=channels, message_id=message.id))
        await itx.followup.send("Select a channel to move the message to:", view=view)
