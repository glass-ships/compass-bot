"""Discord focused utility functions for commands"""

from typing import Union

import discord

from compass_bot.utils.bot_config import EMBED_COLOR
from compass_bot.utils.utils import chunk_list, download, getfilepath


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
    embed = discord.Embed(title=title, description=description, color=EMBED_COLOR())
    if image:
        embed.set_image(url=image)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if footer or footer_image:
        embed.set_footer(text=footer, icon_url=footer_image)
    await channel.send(embed=embed)
    return


async def send_embed_long(
    *,
    channel: discord.TextChannel,
    title=None,
    description=None,  # Union[str, List[str]]
    image=None,
    thumbnail=None,
    footer=None,
    footer_image=None,
):
    """Send potentially too-long embed to channel

    Args:
        channel (discord.TextChannel): Channel to send embed to
        title (str): Title of embed (Default: None)
        description (Union[str, List[str]]): Description of embed (Default: None)
        image (str): URL of image to include in embed (Default: None)
        thumbnail (str): URL of thumbnail to include in embed (Default: None)
        footer (str): Footer text (Default: None)
        footer_image (str): URL of footer image (Default: None)
    """
    if description and len(description) < 4000:
        embed = discord.Embed(title=title, description=description, color=EMBED_COLOR())
        if image:
            embed.set_image(url=image)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        if footer or footer_image:
            embed.set_footer(text=footer, icon_url=footer_image)
        await channel.send(embed=embed)
        return
    elif description and len(description) >= 4000:
        # split into multiple messages
        num_msgs = len(description) // 4000 + 1
        chunked = list(chunk_list(description, len(description) // num_msgs))
        page = 1
        for sublist in chunked:
            embed = discord.Embed(
                title=f"{title} (Page {page}/{num_msgs})",
                description="\n".join(sublist),
            )
            page += 1
            if image:
                embed.set_image(url=image)
            if thumbnail:
                embed.set_thumbnail(url=thumbnail)
            if footer or footer_image:
                embed.set_footer(text=footer, icon_url=footer_image)
            await channel.send(embed=embed)


async def move_message(itx: discord.Interaction, channel: Union[discord.TextChannel, discord.Thread], message_id: str):
    await itx.response.defer(ephemeral=True)
    # Get message to be moved
    msg = await itx.channel.fetch_message(int(message_id))
    newmsg = f"""
{msg.author.mention} - your message from <#{msg.channel.id}> has been moved to the appropriate channel.
─── **Original Message** ───

{msg.content}
"""
    # Get any attachments
    files = []
    if msg.attachments:
        for a in filter(lambda x: x.size <= itx.guild.filesize_limit, msg.attachments):
            await download(itx, a, "temp/moved_messages")
            files.append(discord.File(getfilepath(itx, f"temp/moved_messages/{a.filename}")))
    if any(a.size >= itx.guild.filesize_limit for a in msg.attachments):
        newmsg += (
            f"`File: {a.filename} too large to resend`"
            if len(msg.attachments) == 1
            else f"`Plus some files too large to resend`"
        )

    # Move the message
    new_message = await channel.send(content=newmsg, files=files)
    await msg.delete()
    await itx.followup.send(f"Message moved to {new_message.jump_url}")
