import re
import aiohttp
from typing import Optional
from datetime import datetime
import dateutil.parser as dparser
from urllib import parse as url_parse

from nextcord.ext import commands

from core import utils, i18n

_ = i18n.Translator("modules/fun").translate


class UrbanItem:
    __slots__ = ["word", "definition", "example", "permalink", "author", "written_on"]

    def __init__(
        self,
        word: str = None,
        definition: str = None,
        example: str = None,
        permalink: str = None,
        author: str = None,
        written_on: datetime = None,
    ):
        self.word = word
        self.definition = definition
        self.example = example
        self.permalink = permalink
        self.author = author
        self.written_on = written_on

    def __repr__(self):
        return (
            f'<UrbanItem word="{self.word}" definition="{self.definition}" '
            f'example="{self.example}" permalink="{self.permalink}" '
            f'author="{self.author}" written_on="{self.written_on}">'
        )


class Urban(commands.Cog):
    """Urbandictionary search"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def _create_embeds(ctx: commands.Context, urban_list: list[UrbanItem]):
        embed_list = []

        for item in urban_list:
            if len(item.definition) > 1024:
                item.definition = item.definition[0:1021] + "`…`"
            if len(item.example) > 1024:
                item.example = item.example[0:1021] + "`…`"

            embed = utils.Discord.create_embed(
                author=ctx.message.author,
                title=item.word,
                url=item.permalink,
            )
            if item.definition != "":
                embed.add_field(name="Definition", value=item.definition, inline=False)
            if item.example != "":
                embed.add_field(name="Example", value=item.example, inline=False)

            embed_list.append(embed)
        return embed_list

    @commands.cooldown(rate=5, per=20.0, type=commands.BucketType.user)
    @commands.command()
    async def urban(self, ctx: commands.Context, search_term: Optional[str] = None):
        """Urbandictionary from the comfort of your discord server"""
        if search_term is None:
            await ctx.send(
                ">>> "
                + _(
                    ctx,
                    "Ask me what you want to know and I will answer.",
                )
            )
            return

        term = url_parse.quote(search_term)
        async with ctx.typing():
            try:
                async with aiohttp.ClientSession(raise_for_status=True) as session:
                    async with session.get(
                        f"http://api.urbandictionary.com/v0/define?term={term}"
                    ) as response:
                        json_response = await response.json()
                        lis = json_response["list"]

            except aiohttp.ClientResponseError as e:
                await ctx.reply(
                    _(ctx, "Command encountered an error (E{code}).").format(
                        code=e.status
                    )
                )
                return
            else:
                # Request was successful
                urban_list = []
                for item in lis:
                    urban_item = UrbanItem(
                        item["word"],
                        re.sub(r"[!\[]|[!\]]", "**", item["definition"]),
                        re.sub(r"[!\[]|[!\]]", "**", item["example"]),
                        item["permalink"],
                        item["author"],
                        dparser.parse(item["written_on"]),
                    )
                    urban_list.append(urban_item)

                if urban_list != []:
                    embeds = self._create_embeds(ctx, urban_list)
                else:
                    await ctx.reply("No results found.")
                    return

        scrollable_embed = utils.ScrollableEmbed(ctx, embeds)
        await scrollable_embed.scroll()


def setup(bot) -> None:
    bot.add_cog(Urban(bot))
