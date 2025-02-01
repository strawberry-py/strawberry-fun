from typing import Union

import discord
from discord import app_commands

from pie.i18n import TranslationContext

from ..ZodiacSign import ZodiacSign


class HoroscopeSource:
    """Base class for Horoscope sources. The method `get` must be overwritten.
    Any subclass in the sources folder is considered a source and added to
    sources variable in __init__.py.

    :param sign: Zodiac sign to generate embed for
    :param utx: Translation context
    """

    name: str = __name__  # Can be overwriten

    def __init__(
        self, sign: ZodiacSign, utx: Union[discord.Interaction, TranslationContext]
    ):
        self.sign = sign
        self.utx = utx

    def __ring_key__(self):
        return self.sign.name

    @classmethod
    def choice(cls) -> tuple[str, app_commands.Choice]:
        """Generates app_commands Choice for Zodiac module"""
        return app_commands.Choice(name=cls.name, value=cls.name)

    async def get(self) -> discord.Embed:
        raise NotImplementedError("ZodiacSource get function not overwritten!")
