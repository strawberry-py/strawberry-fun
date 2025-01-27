from discord.ext import commands
from pie import check, logger, i18n
from pie.bot import Strawberry
from discord import app_commands
import discord
from .sources.HoroskopyCZ import HoroskopyCZ
from .ZodiacSign import ZodiacSign

_ = i18n.Translator("modules/fun").translate

class Zodiac(commands.Cog):
    def __init__(self, bot: Strawberry):
        self.bot = bot

    @app_commands.guild_only()
    @check.acl2(check.ACLevel.MEMBER)
    @app_commands.command(name="zodiac")
    async def zodiac(self, itx: discord.Interaction):
        embed = await HoroskopyCZ(ZodiacSign.ARIES, tx=itx).get()
        await itx.response.send_message(embed=embed) 

async def setup(bot: Strawberry):
    await bot.add_cog(Zodiac(bot))