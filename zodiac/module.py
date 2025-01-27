import discord
from discord import app_commands
from discord.ext import commands

from pie import check, i18n
from pie.bot import Strawberry

from .sources import ZodiacSource, sources
from .ZodiacSign import ZodiacSign

_ = i18n.Translator("modules/fun").translate


class Zodiac(commands.Cog):
    def __init__(self, bot: Strawberry):
        self.bot = bot

    @app_commands.guild_only()
    @check.acl2(check.ACLevel.MEMBER)
    @app_commands.command(name="zodiac")
    @app_commands.choices(source=[source.choice() for source in sources.values()])
    async def zodiac(self, itx: discord.Interaction, source: str):
        source_instance: ZodiacSource = sources[source](ZodiacSign.ARIES, tx=itx)
        embed = await source_instance.get()
        await itx.response.send_message(embed=embed)


async def setup(bot: Strawberry):
    await bot.add_cog(Zodiac(bot))
