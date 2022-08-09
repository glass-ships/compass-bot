### Imports ###

from discord.ext import commands
from random import choice
import utils.music_config as config
from utils.helper import * 
from datetime import datetime as dt

logger = get_logger(__name__)
### Setup Cog

# Startup method
async def setup(bot):
    await bot.add_cog(Destiny(bot))

# Define Class
class Destiny(commands.Cog):
    def __init__(self, bot_):
        global bot
        bot = bot_

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")

    # LFM Create
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        lfg_channel = bot.db.get_channel_lfg(message.guild.id)
        if lfg_channel == 0 or message.channel.id != lfg_channel:
            return
        
        msg = message.content
        lfm_format = r'[Ll][Ff]\d[Mm]'
        search = re.search(lfm_format, msg)
        if search is None:
            return

        num_players = int(search.group()[2])
        bot.db.add_lfg(guild_id=message.guild.id, lfg_id=message.id, user_id=message.author.id, num_players=num_players)

        await message.add_reaction('<:_plus:1000298488908746792>')
        await message.add_reaction('<:_minus:1000298486643830855>')
        await message.add_reaction('📖')

        embed = discord.Embed(
            title="LFG session created!",
            color=choice(config.EMBED_COLORS),
	        description="React with 📖 to see your active roster.\n\n**Note:** Please do not edit your post, as our bot will automatically react with 🇫 when session is full.",
        )
        embed.set_footer(text=f"Fireteam Leader: {message.author.nick}", icon_url=message.author.avatar.url)
        await message.channel.send(embed=embed, delete_after=7.0)
        await asyncio.sleep(3600)
        bot.db.drop_lfg(message.guild.id, message.id)

    # LFM Update (Join/Leave/Check)
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member.bot:
            return

        guild = bot.get_guild(payload.guild_id)
        channel = bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        user = payload.member
        
        lfg_channel = bot.db.get_channel_lfg(guild.id)
        if lfg_channel == 0 or message.channel.id != lfg_channel:
            return
                         
        emojis = {
            'join':'_plus',
            'leave':'_minus',
            'book':'📖',
            'full':'🇫'
            }
                
        lfg = bot.db.get_lfg(guild_id=guild.id, lfg_id=payload.message_id)

        if payload.emoji.name == emojis['join']:
            await message.remove_reaction(payload.emoji, user)
            if lfg == None:
                embed = discord.Embed(title="Inactive Post", description="This post is more than 60 minutes old and has expired.")
                await channel.send(embed=embed, delete_after=10.0)
                return
            if user.id == lfg['leader']:
                return
            if len(lfg['joined'])+1 == lfg['num_players']:
                await message.add_reaction(emojis['full'])
            bot.db.update_lfg_join(guild_id=guild.id, lfg_id=payload.message_id, user_id=payload.user_id)
            embed = discord.Embed()
            embed.add_field(name=f'{user.nick or user.name} has joined your LFG', value=f'To view your roster, react to [your post]({message.jump_url}) with the {emojis["book"]} emoji.')
            await channel.send(
                content=f'{message.author.mention}',
                embed=embed,
                delete_after=10.0
            )
        elif payload.emoji.name == emojis['leave']:
            await message.remove_reaction(payload.emoji, user)
            if lfg == None:
                embed = discord.Embed(title="Inactive Post", description="This post is more than 60 minutes old and has expired.")
                await channel.send(embed=embed, delete_after=10.0)
                return
            if user.id == lfg['leader']:
                return
            if len(lfg['joined'])-1 < lfg['num_players']:
                await message.remove_reaction(emojis['full'], guild.get_member(bot.user.id))
            bot.db.update_lfg_leave(guild_id=guild.id, lfg_id=payload.message_id, user_id=payload.user_id)
            embed = discord.Embed()
            embed.add_field(name=f'{user.nick or user.name} has left your LFG', value=f'To view your roster, react to [your post]({message.jump_url}) with the {emojis["book"]} emoji.')
            await channel.send(
                content=f'{message.author.mention}',
                embed=embed,
                delete_after=10.0
            )
        elif payload.emoji.name == emojis['book']:
            await message.remove_reaction(payload.emoji, user)
            if lfg == None:
                embed = discord.Embed(title="Inactive Post", description="This post is more than 60 minutes old and has expired.")
                await channel.send(embed=embed, delete_after=10.0)
                return
            embed = discord.Embed(
                title=f"{message.author.name}'s LFG",
                color=choice(config.EMBED_COLORS),
            )
            embed.set_thumbnail(url=message.author.avatar.url)
            
            fireteam = ''
            fireteam += f"<@{lfg['leader']}>\n"
            for i in lfg['joined']:
                fireteam += f"<@{i}>\n"
            embed.add_field(name="Fireteam", value=fireteam)
            
            if len(lfg['standby']) > 0:
                standby = ''
                for i in lfg['standby']:
                    standby += f"<@{i}>\n"
                embed.add_field(name='Standby', value=standby)

            embed.set_footer(text=f"Requested by: {user.nick or user.name}")
            await bot.get_channel(payload.channel_id).send(embed=embed, delete_after=10.0)

    @commands.command(name='checkmembers', aliases=['members', 'cm'])
    async def _check_members(self, ctx):
        """End Game specific: Get a list of members/veterans"""
        # Check for mod
        mod_roles = bot.db.get_mod_roles(ctx.guild.id)
        if not await role_check(ctx, mod_roles):
            return
        
        vet = get(ctx.guild.roles, id=889212097706217493)
        mem = get(ctx.guild.roles, id=780536143556116530)
        #vet = get(ctx.guild.roles, id=594462694103318530)
        #mem = get(ctx.guild.roles, id=594462177553809438)

        vets, mems, both = ([] for i in range(3))
        for user in ctx.guild.members:
            if (vet in user.roles and mem not in user.roles):
                vets.append([user.mention, int(dt.timestamp(user.joined_at))])
            if (mem in user.roles and vet not in user.roles):
                mems.append([user.mention, int(dt.timestamp(user.joined_at))])
            if (vet in user.roles and mem in user.roles):
                both.append([user.mention, int(dt.timestamp(user.joined_at))])

        vets = sorted(vets, key=lambda x: x[1], reverse=False)
        mems = sorted(mems, key=lambda x: x[1], reverse=False)
        both = sorted(both, key=lambda x: x[1], reverse=False)

        vets_str, mems_str, both_str = [""]*3
        for i in vets:
            vets_str += f"{i[0]} - Joined <t:{i[1]}:R>\n"
        for i in mems:
            mems_str += f"{i[0]} - Joined <t:{i[1]}:R>\n"
        for i in both:
            both_str += f"{i[0]} - Joined <t:{i[1]}:R>\n"
        embed = discord.Embed(
            title="Members and Veterans",
            description=f"""
                __**Non-Veteran Members ({len(mems)}):**__\n{mems_str}\n
                __**Veteran Members ({len(both)}):**__\n{both_str}\n
                __**Veterans Not in a Clan ({len(vets)}):**__\n{vets_str}
            """
        )
        await ctx.send(embed=embed)
