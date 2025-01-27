import discord

from .ZodiacSign import ZodiacSign


class ZodiacSource:
    def __init__(self, sign: ZodiacSign):
        self.sign = sign

    async def get(self) -> discord.Embed:
        raise NotImplementedError("ZodiacSign scrape not overwritten!")
