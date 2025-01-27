from enum import Enum
from typing import Union

import discord
from discord import app_commands
from discord.ext import commands

from pie import i18n

_ = i18n.Translator("modules/fun").translate


class ZodiacSign(Enum):
    ARIES = app_commands.Choice(name="Aries", value=1)
    TAURUS = app_commands.Choice(name="Taurus", value=2)
    GEMINI = app_commands.Choice(name="Gemini", value=3)
    CANCER = app_commands.Choice(name="Cancer", value=4)
    LEO = app_commands.Choice(name="Leo", value=5)
    VIRGO = app_commands.Choice(name="Virgo", value=6)
    LIBRA = app_commands.Choice(name="Libra", value=7)
    SCORPIUS = app_commands.Choice(name="Scorpius", value=8)
    SAGITTARIUS = app_commands.Choice(name="Sagittarius", value=9)
    CAPRICORN = app_commands.Choice(name="Capricorn", value=10)
    AQUARIUS = app_commands.Choice(name="Aquarius", value=11)
    PISCES = app_commands.Choice(name="Pisces", value=12)

    def translate(
        self, utx: Union[commands.Context, discord.Interaction, i18n.TranslationContext]
    ) -> str:
        """Function that translate name of the zodiac sign.

        :param utx: Translation context
        :return: Translated name
        """
        if self == ZodiacSign.ARIES:
            return _(utx, "Aries")
        if self == ZodiacSign.TAURUS:
            return _(utx, "Taurus")
        if self == ZodiacSign.GEMINI:
            return _(utx, "Gemini")
        if self == ZodiacSign.CANCER:
            return _(utx, "Cancer")
        if self == ZodiacSign.LEO:
            return _(utx, "Leo")
        if self == ZodiacSign.VIRGO:
            return _(utx, "Virgo")
        if self == ZodiacSign.LIBRA:
            return _(utx, "Libra")
        if self == ZodiacSign.SCORPIUS:
            return _(utx, "Scorpius")
        if self == ZodiacSign.SAGITTARIUS:
            return _(utx, "Sagittarius")
        if self == ZodiacSign.CAPRICORN:
            return _(utx, "Capricorn")
        if self == ZodiacSign.AQUARIUS:
            return _(utx, "Aquarius")
        if self == ZodiacSign.PISCES:
            return _(utx, "Pisces")

    @property
    def emoji(self) -> str:
        """Function that returns the zodiac emoji.

        :return: utf-8 emoji
        """
        if self == ZodiacSign.ARIES:
            return "♈"
        if self == ZodiacSign.TAURUS:
            return "♉"
        if self == ZodiacSign.GEMINI:
            return "♊"
        if self == ZodiacSign.CANCER:
            return "♋"
        if self == ZodiacSign.LEO:
            return "♌"
        if self == ZodiacSign.VIRGO:
            return "♍"
        if self == ZodiacSign.LIBRA:
            return "♎"
        if self == ZodiacSign.SCORPIUS:
            return "♏"
        if self == ZodiacSign.SAGITTARIUS:
            return "♐"
        if self == ZodiacSign.CAPRICORN:
            return "♑"
        if self == ZodiacSign.AQUARIUS:
            return "♒"
        if self == ZodiacSign.PISCES:
            return "♓"
