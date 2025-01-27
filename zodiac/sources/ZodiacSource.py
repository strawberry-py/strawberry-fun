from typing import Union

import discord
from discord import app_commands

from pie.i18n import TranslationContext

from ..ZodiacSign import ZodiacSign


class ZodiacSource:
    name: str = __name__  # Can be overwriten

    def __init__(
        self, sign: ZodiacSign, tx: Union[discord.Interaction, TranslationContext]
    ):
        self.sign = sign
        self.tx = tx

    @classmethod
    def choice(cls) -> tuple[str, app_commands.Choice]:
        """Generates app_commands Choice for Zodiac module"""
        return app_commands.Choice(name=cls.name, value=cls.name)

    async def get(self) -> discord.Embed:
        raise NotImplementedError("ZodiacSource get function not overwritten!")
