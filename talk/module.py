from __future__ import annotations

import enum
from typing import List

import discord
import requests
import ring
from discord import app_commands
from discord.ext import commands
from openai import AsyncOpenAI, _types

from pie import check, i18n, logger, storage, utils

_ = i18n.Translator("modules/fun").translate
bot_log = logger.Bot.logger()
guild_log = logger.Guild.logger()


class TalkConfig(enum.Enum):
    MODEL = app_commands.Choice(name="MODEL", value="MODEL")
    MAXTOKENS = app_commands.Choice(name="MAXTOKENS", value="MAXTOKENS")
    APIKEY = app_commands.Choice(name="APIKEY", value="APIKEY")

    @staticmethod
    def values() -> List[app_commands.Choice]:
        return [e.value for e in TalkConfig]

    @staticmethod
    def names() -> List[str]:
        return [str(e.name) for e in TalkConfig]


class Talk(commands.Cog):

    MIN_LENGTH = 5
    MAX_LENGTH = 200

    talk_admin = app_commands.Group(
        name="talkadmin", description="Talk management commands."
    )

    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    @check.acl2(check.ACLevel.MEMBER)
    @app_commands.command(name="talk", description="Talk with the bot.")
    @app_commands.describe(
        message="Message with length between {} and {} characters.".format(
            MIN_LENGTH, MAX_LENGTH
        )
    )
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.checks.cooldown(10, 60, key=lambda i: i.guild_id)
    async def talk(self, itx: discord.Interaction, message: str):
        key: str = await self._get_key(itx)
        if not key:
            return

        model = storage.get(self, guild_id=itx.guild_id, key="MODEL")

        if not model:
            await itx.response.send_message(
                _(
                    itx,
                    "Language model not set. See `/talkadmin set` or ask Discord admin to set this up.",
                )
            )
            return

        if not message or len(message) < Talk.MIN_LENGTH:
            await itx.response.send_message(
                _(itx, "Message must be at least {} characters long.").format(
                    Talk.MIN_LENGTH
                )
            )
            return

        if len(message) > Talk.MAX_LENGTH:
            await itx.response.send_message(
                _(itx, "Message must be shorter than {} characters.").format(
                    Talk.MAX_LENGTH
                )
            )
            return

        await itx.response.send_message(
            _(itx, "{user} said: `{message}`").format(
                user=itx.user.mention, message=message
            )
        )
        response = await itx.original_response()

        max_tokens = storage.get(
            self, guild_id=itx.guild.id, key="MAXTOKENS", default_value=_types.NOT_GIVEN
        )
        if not max_tokens or max_tokens < 1:
            max_tokens = _types.NOT_GIVEN

        async with itx.channel.typing():
            client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=key,
            )

            try:
                completion = await client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": "https://github.com/strawberry-py",
                        "X-Title": "Strawberry.py - " + self.bot.user.name,
                    },
                    model=model,
                    max_tokens=max_tokens,
                    messages=[
                        {
                            "role": "user",
                            "content": message,
                        },
                    ],
                )
                message = completion.choices[0].message.content
                for part in utils.text.split(message):
                    response = await response.reply(part)

            except Exception as ex:
                await response.reply(
                    _(
                        itx,
                        "My brain is not in great shape right now. Might answer later...",
                    )
                )
                await guild_log.error(
                    itx.user, itx.channel, "An error occured.", exception=ex
                )

    @check.acl2(check.ACLevel.MOD)
    @talk_admin.command(
        name="info", description="Get info on current talk configuration."
    )
    async def talk_admin_info(self, itx: discord.Interaction):
        key = await self._get_key(itx)

        tokens = storage.get(self, guild_id=itx.guild.id, key="MAXTOKENS")

        if not tokens:
            tokens = _(itx, "default")

        if not key:
            return
        message = (
            _(itx, "API Key is set.")
            + "\n"
            + _(itx, "Current model: `{model}`.").format(
                model=storage.get(self, guild_id=itx.guild_id, key="MODEL")
            )
            + "\n"
            + _(itx, "Max tokens: `{tokens}`.").format(tokens=tokens)
        )
        await itx.response.send_message(message, ephemeral=True)

    @check.acl2(check.ACLevel.MOD)
    @talk_admin.command(name="models", description="Get list of models.")
    async def talk_admin_models(self, itx: discord.Interaction):
        await itx.response.send_message(
            "See: https://openrouter.ai/models", ephemeral=True
        )

    @check.acl2(check.ACLevel.MOD)
    @talk_admin.command(name="set", description="Set talk configuration.")
    @app_commands.choices(config=TalkConfig.values())
    async def talk_admin_set(
        self,
        itx: discord.Interaction,
        config: app_commands.Choice[str],
        value: str,
    ):
        await itx.response.send_message(_(itx, "Working on it..."), ephemeral=True)
        if config == TalkConfig.APIKEY:
            storage.set(self, itx.guild_id, key=TalkConfig.APIKEY.name, value=value)
        elif config == TalkConfig.MODEL:
            if await self._verify_model(itx, value):
                storage.set(self, itx.guild.id, key=TalkConfig.MODEL.name, value=value)
        elif config == TalkConfig.MAXTOKENS:
            try:
                value = int(value)
            except ValueError:
                await (await itx.original_response()).edit(
                    content=_(
                        itx, "Value of MAXTOKENS must be a number higher or equal 1."
                    )
                )
                return
            if value < 1:
                await (await itx.original_response()).edit(
                    content=_(
                        itx, "Value of MAXTOKENS must be a number higher or equal 1."
                    )
                )
                return

            storage.set(self, itx.guild_id, key=TalkConfig.MAXTOKENS.name, value=value)
        else:
            await (await itx.original_response()).edit(
                content=_(
                    itx, "Invalid config {config}. Allowed values are: {configs}."
                ).format(config=config.value, configs=", ".join(TalkConfig.names()))
            )
            return
        await (await itx.original_response()).edit(
            content=_(itx, "Config {config} successfuly set.").format(
                config=config.value
            )
        )

    @check.acl2(check.ACLevel.MOD)
    @talk_admin.command(name="unset", description="Unset talk configuration.")
    @app_commands.choices(config=[TalkConfig.APIKEY.value, TalkConfig.MAXTOKENS.value])
    async def talk_admin_unset(
        self,
        itx: discord.Interaction,
        config: app_commands.Choice[str],
    ):
        if config == TalkConfig.APIKEY:
            storage.unset(self, itx.guild.id, TalkConfig.APIKEY.name)
        elif config == TalkConfig.MAXTOKENS:
            storage.unset(self, itx.guild.id, TalkConfig.MAXTOKENS.name)
        else:
            await (await itx.original_response()).edit(
                content=_(
                    itx, "Invalid config {config}. Allowed values are: {configs}."
                ).format(
                    config=config.value,
                    configs=", ".join(
                        [TalkConfig.APIKEY.value, TalkConfig.MAXTOKENS.value]
                    ),
                )
            )

        await itx.response.send_message(
            content=_(itx, "Config {config} successfuly unset.").format(
                config=config.value
            )
        )

    async def _verify_model(self, itx: discord.Interaction, model: str):
        key = await self._get_key(itx=itx)
        if not key:
            return
        try:
            models: List[str] = await self._list_models(key)
        except Exception as ex:
            await (await itx.original_response()).edit(
                content=_(itx, "An error occured during model check."),
            )
            await guild_log.error(
                itx.user, itx.channel, "An error occured.", exception=ex
            )
            return False

        if model not in models:
            await (await itx.original_response()).edit(
                content=_(
                    itx, "Unknown / unsupported model. See https://openrouter.ai/models"
                ),
            )
            return False

        return True

    @ring.lru(expire=60, force_asyncio=True)
    async def _list_models(self, key):
        url = "https://openrouter.ai/api/v1/models"
        headers = {
            "Authorization": f"Bearer {key}",
        }

        result = requests.get(url, headers=headers)
        models = result.json()["data"]

        return [model["id"] for model in models]

    async def _get_key(self, itx: discord.Interaction) -> str | None:
        key = storage.get(self, itx.guild_id, "APIKEY", None)
        if not key:
            await itx.response.send_message(
                _(
                    itx,
                    "API key not set. See `/talkadmin set` or ask Discord admin to set this up.",
                ),
                ephemeral=True,
            )
            return None
        return key

    def __ring_key__(self):
        """Allow ring.lru(), as it requires `self` argument."""
        return "talk"


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Talk(bot))
