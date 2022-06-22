### Imports ###

#import discord
#from discord.utils import get
from discord.ext import commands

from utils.helper import * 

logger = get_logger(__name__)
### Setup Cog

# Startup method
async def setup(bot):
    await bot.add_cog(Destiny(bot))

# Define Class
class Destiny(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Cog Online: {self.qualified_name}")


    #@app_commands.command(name='nolfg', description="Give a user `Access - No LFG` and dm the user")
    #async def _no_lfg(self, ctx, duration: str, reason: str ):
    #    pass

    @commands.command(name='checkvets')
    async def _check_veterans(self, ctx):
        # Check for mod
        logger.info("Checking for mod role...")
        mod_roles = self.bot.db.get_mod_roles(ctx.guild.id)
        if not await role_check(ctx, mod_roles):
            return
        
        vet = get(ctx.guild.roles, id=594462694103318530)
        mem = get(ctx.guild.roles, id=594462177553809438)
        
        vets = []
        mems = []
        both = []
        for user in ctx.guild.members:
            if vet in user.roles and mem not in user.roles:
                vets.append(user.mention)
            if mem in user.roles and vet not in user.roles:
                mems.append(user.mention)
            if vet in user.roles and mem in user.roles:
                both.append(user.mention)
               
        for m in mems:
            if m in vets:
                both.append(m)
        
        embed = discord.Embed(
            title="Members and Veterans",
            description=f"""
                - Members with Veteran ({len(both)}): {both}\n\n
                - Veterans not in the clan ({len(vets)}): {vets}
            """
        )
        await ctx.send(embed=embed)