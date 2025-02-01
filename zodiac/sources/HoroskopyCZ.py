import re
from typing import Optional

import aiohttp
import ring
from bs4 import BeautifulSoup

import discord

from pie import i18n, utils

from ..ZodiacSign import ZodiacSign
from .HoroscopeSource import HoroscopeSource

_ = i18n.Translator("modules/fun").translate

# last part of URL based on sign
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


class HoroskopyCZ(HoroscopeSource):
    name = "Horoskopy.CZ"

    @property
    def url(self):
        return "https://horoskopy.cz/" + ZODIAC_URL[self.sign]

    async def get(self) -> discord.Embed:
        """Generate embed with horoscope or error description."""
        try:
            return await self.generate_embed(web_content=await self.get_web_content())
        except aiohttp.ClientError as ex:
            return self.generate_error_embed(ex)

    @ring.lru(expire=60, force_asyncio=True)
    async def get_web_content(self) -> Optional[str]:
        """Gets web content based on sign.

        :return: Web content as string.
        :raises aiohttp.ClientError: If respons is not 200 or can't connect."""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as resp:
                if resp.status != 200:
                    raise aiohttp.ClientError(str(resp.status))
                return await resp.text()

    async def generate_embed(self, web_content: str) -> discord.Embed:
        """Scrape web content and generate embed with content.

        :return: Horoscope embed."""
        soup = BeautifulSoup(web_content, "html.parser")
        embed: discord.Embed = utils.discord.create_embed(
            title=f"Horoskop na dnešní den - {self.sign.translate(self.utx)} {self.sign.emoji}",
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

    def generate_error_embed(self, ex: Exception) -> discord.Embed:
        """Generate error embed.

        :return: Error embed."""
        embed: discord.Embed = utils.discord.create_embed(
            title=_(self.utx, "A network error has occurred."),
            description=str(ex),
            url=self.url,
            error=True,
        )

        return embed

    def get_text(self, soup: BeautifulSoup, header_text: str) -> str:
        """Get text from web based on header.

        :return: Scraped text."""
        header = soup.find(string=re.compile(header_text))
        content = header.find_next("p").text.strip()
        return content
