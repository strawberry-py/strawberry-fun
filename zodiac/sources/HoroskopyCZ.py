import discord
import aiohttp
from bs4 import BeautifulSoup
import re
from pie import utils

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
    ZodiacSign.CAPRICORN: "kozoroh",
    ZodiacSign.AQUARIUS: "vodnar",
    ZodiacSign.PISCES: "ryby",
}


class HoroskopyCZ(ZodiacSource):
    @property
    def url(self):
        return "https://horoskopy.cz/" + ZODIAC_URL[self.sign]

    async def get(
        self,
    ) -> (
        discord.Embed
    ):  # Bude vracet výsledný embed (text v embedu) nebo embed s chybou
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url) as resp:
                    if resp.status != 200:
                        return None  # TODO - vrátit embed s chybou
                    return await self.generate_embed(web_content=await resp.text())
        except aiohttp.ClientError:
            return None  # TODO - vrátit embed s chybou

    async def generate_embed(self, web_content: str) -> discord.Embed:
        soup = BeautifulSoup(web_content, "html.parser")
        embed: discord.Embed = utils.discord.create_embed(
            title="Horoskop na dnešní den",
            description=self.get_text(soup=soup, header_text="Horoskop na dnešní den"),
            url=self.url,
        )
        headers = [
            "Láska a přátelství",
            "Peníze a práce",
            "Rodina a vztahy",
            "Zdraví a kondice",
            "Aktivity vhodné pro dnešní den",
        ]
        for header in headers:
            content = self.get_text(soup=soup, header_text=header)
            embed.add_field(name=header, value=content, inline=False)

        return embed

    def get_text(self, soup: BeautifulSoup, header_text: str) -> str:
        header = soup.find(string=re.compile(header_text))
        content = header.find_next("p").text.strip()
        return content
