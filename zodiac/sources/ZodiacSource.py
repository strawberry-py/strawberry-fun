from typing import Union

import discord

from pie.i18n import TranslationContext

from ..ZodiacSign import ZodiacSign


class ZodiacSource:
    def __init__(
        self, sign: ZodiacSign, tx: Union[discord.Interaction, TranslationContext]
    ):
        self.sign = sign
        self.tx = tx

    async def get(self) -> discord.Embed:
        raise NotImplementedError("ZodiacSource get function not overwritten!")
