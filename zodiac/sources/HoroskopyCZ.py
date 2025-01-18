import discord

from ..ZodiacSign import ZodiacSign
from ..ZodiacSource import ZodiacSource

ZODIAC_URL = {
    ZodiacSign.ARIES: "beran",
    ZodiacSign.TAURUS: "byk",
    ZodiacSign.GEMINI: "blizenci",
    ZodiacSign.CANCER: "rak",
    ZodiacSign.LEO: "lev",
    ZodiacSign.VIRGO: "panna",
    ZodiacSign.LIBRA: "vahy",
    ZodiacSign.SCORPIUS: "stir",
    ZodiacSign.SAGITTARIUS: "strelec",
    ZodiacSign.CAPRICORNUS: "kozoroh",
    ZodiacSign.AQUARIUS: "vodnar",
    ZodiacSign.PISCES: "ryby",
}


class HoroskopyCZ(ZodiacSource):
    def get(self) -> discord.Embed:  # Bude vracet výsledný embed (text v embedu)
        pass
