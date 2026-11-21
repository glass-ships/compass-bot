"""Discord focused utility functions for commands"""

import discord

from compass.config.bot_config import COLORS
from compass.utils.utils import download, getfilepath


def get_emojis(guild: discord.Guild) -> tuple[list[discord.Emoji], list[discord.Emoji]]:
    """Returns lists of all static and animated emojis in a guild"""

    emojis = {"anim": [], "static": []}
    for i in guild.emojis:
        if i.animated is True:
            emojis["anim"].append(i)
        else:
            emojis["static"].append(i)
    return emojis["static"], emojis["anim"]


async def send_embed(
    *,
    channel: discord.TextChannel,
    title=None,
    description=None,
    image=None,
    thumbnail=None,
    footer=None,
    footer_image=None,
):
    """Send embed to channel

    Args:
        channel (discord.TextChannel): Channel to send embed to
        title (str): Title of embed (Default: None)
        description (Union[str, List[str]]): Description of embed (Default: None)
        image (str): URL of image to include in embed (Default: None)
        thumbnail (str): URL of thumbnail to include in embed (Default: None)
        footer (str): Footer text (Default: None)
        footer_image (str): URL of footer image (Default: None)
    """
    embed = discord.Embed(title=title, description=description, color=COLORS().random())
    if image:
        embed.set_image(url=image)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if footer or footer_image:
        embed.set_footer(text=footer, icon_url=footer_image)
    await channel.send(embed=embed)
    return


EMBED_DESC_LIMIT = 4096  # Discord's max embed description length


def paginate(text: str, limit: int = EMBED_DESC_LIMIT) -> list[str]:
    """Split text into pages of at most `limit` chars, breaking on newlines where possible.

    Lines longer than `limit` are hard-split. Multi-line markdown (code blocks, `>>>` quotes)
    is not carried across page breaks.
    """
    # TODO: close/reopen code blocks and `>>>` quotes across page breaks, and prefer breaking
    # long lines at spaces (see plans/todo.md)
    pages, cur = [], ""
    for line in text.splitlines():
        while len(line) > limit:  # a single line too long for one page: hard-split it
            if cur:
                pages.append(cur)
                cur = ""
            pages.append(line[:limit])
            line = line[limit:]
        if cur and len(cur) + 1 + len(line) > limit:
            pages.append(cur)
            cur = line
        else:
            cur = f"{cur}\n{line}" if cur else line
    if cur:
        pages.append(cur)
    return pages


async def send_embed_long(
    *,
    channel: discord.abc.Messageable,
    title: str | None = None,
    description: str | list[str] | None = None,
    image: str | None = None,
    thumbnail: str | None = None,
    footer: str | None = None,
    footer_image: str | None = None,
):
    """Send an embed, split across multiple messages if the description is too long.

    Pages break on newlines. The thumbnail goes on the first page; the image and footer on the last.

    Args:
        channel (discord.abc.Messageable): Channel to send embed to
        title (str): Title of embed; pages get a " (Page i/n)" suffix (Default: None)
        description (str | list[str]): Description of embed; a list is joined with newlines (Default: None)
        image (str): URL of image to include in embed (Default: None)
        thumbnail (str): URL of thumbnail to include in embed (Default: None)
        footer (str): Footer text (Default: None)
        footer_image (str): URL of footer image (Default: None)
    """
    if isinstance(description, list):
        description = "\n".join(description)
    pages = paginate(description or "") or [""]
    color = COLORS().random()
    for i, page in enumerate(pages, 1):
        page_title = title if len(pages) == 1 else f"{title or ''} (Page {i}/{len(pages)})".strip()
        embed = discord.Embed(title=page_title, description=page or None, color=color)
        if i == 1 and thumbnail:
            embed.set_thumbnail(url=thumbnail)
        if i == len(pages):
            if image:
                embed.set_image(url=image)
            if footer or footer_image:
                embed.set_footer(text=footer, icon_url=footer_image)
        await channel.send(embed=embed)


async def move_message(itx: discord.Interaction, channel: discord.TextChannel | discord.Thread, message_id: str):
    await itx.response.defer(ephemeral=True)
    assert itx.channel is not None
    if not isinstance(itx.channel, (discord.TextChannel, discord.Thread)):
        await itx.followup.send("Unable to move messages from a category or forum channel", ephemeral=True)
        return
    message_id = message_id.split("-")[-1]
    msg = await itx.channel.fetch_message(int(message_id))
    newmsg = f"""
{msg.author.mention}, your message from <#{msg.channel.id}> has been moved to the appropriate channel.

-# **__Original Message:__**
>>> {msg.content}
"""
    # Get any attachments
    files = []
    if msg.attachments:
        if any(a.size >= itx.guild.filesize_limit for a in msg.attachments):
            newmsg += "`Plus some files too large to resend`"
        for a in filter(lambda x: x.size <= itx.guild.filesize_limit, msg.attachments):
            await download(msg, a, "temp/moved_messages")
            files.append(discord.File(getfilepath(itx, f"temp/moved_messages/{a.filename}")))

    # Move the message
    new_message = await channel.send(content=newmsg, files=files)
    await msg.delete()
    await itx.followup.send(f"Message moved to {new_message.jump_url}", ephemeral=True)
