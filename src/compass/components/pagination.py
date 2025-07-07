from typing import Callable, Optional

import discord

from compass.config.bot_config import COLORS


class Pagination(discord.ui.View):
    """Reusable paginated embed component.

    Currently sending responses/followups prior to calling Pagination
    is not supported.

    Attributes:
        itx: the interaction to respond to
        get_page: a callable that returns an embed and total num of pages.

    Usage:
        `await Pagination(itx, some_callable).init()`

        `get_page` should accept a page number (int) as a parameter, and
        - define per_page number of items
        - enumerate entries based on an `offset = (page-1) * per_page`

        For example:
        ```
        per_page = 10
        def _get_page(page: int):
            emb = discord.Embed(
                title="Embed Title",
                description="Some Description",
            )
            offset = (page - 1) * per_page
            n = Pagination.compute_total_pages(len(i), per_page)
            for i in some_iterable[offset : offset + per_page]:
                emb.add_field(name=i.name, value=i.value, inline=False)
            emb.set_author(name=f"Requested by {itx.user}")
            emb.set_footer(text=f"Page {page} of {n}")
            return emb, n
            ```
    """

    def __init__(self, itx: discord.Interaction, get_page: Callable):
        self.itx = itx
        self.get_page = get_page
        self.total_pages: int
        self.index = 1
        super().__init__(timeout=300)

    async def itx_check(self, itx: discord.Interaction) -> bool:
        if itx.user == self.itx.user:
            return True
        else:
            emb = discord.Embed(
                description=f"Only the author of the command can perform this action.", color=COLORS.random()
            )
            await itx.response.send_message(embed=emb, ephemeral=True)
            return False

    async def init(self):
        emb, self.total_pages = self.get_page(self.index)
        if self.total_pages == 1:
            await self.itx.response.send_message(embed=emb)
        elif self.total_pages > 1:
            self.update_buttons()
            await self.itx.response.send_message(embed=emb, view=self)

    async def edit_page(self, itx: discord.Interaction):
        emb, self.total_pages = self.get_page(self.index)
        self.update_buttons()
        await itx.response.edit_message(embed=emb, view=self)

    def update_buttons(self):
        if self.index > self.total_pages // 2:
            self.children[2].emoji = "⏮️"
        else:
            self.children[2].emoji = "⏭️"
        self.children[0].disabled = self.index == 1
        self.children[1].disabled = self.index == self.total_pages

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.blurple)
    async def previous(self, itx: discord.Interaction, button: discord.ui.Button):
        self.index -= 1
        await self.edit_page(itx)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.blurple)
    async def next(self, itx: discord.Interaction, button: discord.ui.Button):
        self.index += 1
        await self.edit_page(itx)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.blurple)
    async def end(self, itx: discord.Interaction, button: discord.ui.Button):
        if self.index <= self.total_pages // 2:
            self.index = self.total_pages
        else:
            self.index = 1
        await self.edit_page(itx)

    async def on_timeout(self):
        message = await self.itx.original_response()
        await message.edit(view=None)

    @staticmethod
    def compute_total_pages(total_results: int, results_per_page: int) -> int:
        return ((total_results - 1) // results_per_page) + 1
