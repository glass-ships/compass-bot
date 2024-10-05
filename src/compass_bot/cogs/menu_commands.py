from typing import List, Union, Dict

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from compass_bot.utils.command_utils import move_message


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
        options: List[Dict[str, Union[str, int]]],
        message_id: int,
    ) -> None:
        self.message_id = message_id
        super().__init__(
            custom_id="Select a Channel ",
            options=options,
        )

    async def callback(self, itx: discord.Interaction) -> None:
        channel = itx.guild.get_channel(int(self.values[0]))
        await move_message(itx, channel, self.message_id)


class SelectChannelView(discord.ui.View):
    def __init__(self, options: List[Dict[str, Union[str, int]]]) -> None:
        super().__init__()
        self.add_item(SelectMenuChannel(options=options))


class MenuCommands(commands.Cog):
    def __init__(self, bot_: commands.Bot) -> None:
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
                label=channel.name, value=channel.id, description=channel.topic, emoji=None, default=False
            )
            for channel in message.guild.text_channels
        ]
        view = discord.ui.View()
        view.add_item(SelectMenuChannel(options=channels, message_id=message.id))
        # await itx.response.send_message("Select a channel to move the message to:", view=view)
        await itx.followup.send("Select a channel to move the message to:", view=view)
