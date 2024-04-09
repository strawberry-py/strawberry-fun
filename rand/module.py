import hashlib
import random
import re
import urllib
from typing import Any, Dict, List, Optional

import aiohttp
import discord
from discord.ext import commands

from pie import check, i18n, logger, utils

TRANSLATOR = i18n.Translator("modules/fun")
_ = TRANSLATOR.translate
guild_log = logger.Guild.logger()


class Rand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Helpers

    def _get_request_headers(self) -> Dict[str, str]:
        """Generate headers to identify to API.

        Even if some APIs do not require authorization, it is part or the good
        manners to identify us as a client.

        Individual API requirements should be commented here. Unless they are
        contradicting, or unless they contain a secret, they should always be
        sent.
        """
        result: Dict[str, str] = {}
        result["X-strawberry.py-bot"] = str(self.bot.user.id)
        # TODO The URL also appears in mgmt/verify. Should we move it
        #      to somewhere in the core?
        result["X-strawberry.py-url"] = "https://github.com/strawberry-py"
        return result

    async def _get_json_from_api(
        self,
        endpoint_url: str,
        ctx: discord.ext.commands.Context,
        send_reply: bool = True,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Returns json response on success, None otherwise.
        Sends logs and replies in case of an error."""
        headers = self._get_request_headers()
        if params is None or not isinstance(params, dict):
            params = {}
        headers["Accept"] = "application/json"
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(
                    endpoint_url, headers=headers, params=params
                ) as response:
                    if response.status != 200:
                        guild_log.info(
                            ctx.author,
                            ctx.channel,
                            f"Request to '{endpoint_url}' has status cod {response.status}.",
                        )
                        if send_reply:
                            await ctx.reply(
                                _(
                                    ctx, "Command encountered an error (E{code})."
                                ).format(code=response.status)
                            )
                        return

                    return await response.json()

        except aiohttp.ClientError:
            guild_log.warning(
                ctx.author,
                ctx.channel,
                f"Could not contact '{endpoint_url}' due to a network error.",
            )
            if send_reply:
                await ctx.reply(_(ctx, "A network error has occurred."))

    # Commands

    @commands.cooldown(rate=5, per=20.0, type=commands.BucketType.user)
    @check.acl2(check.ACLevel.EVERYONE)
    @commands.command(name="random")
    async def random_(self, ctx, first: int, second: Optional[int] = 0):
        """Generate random number within the interval"""
        if first > second:
            first, second = second, first

        await ctx.reply(random.randint(first, second))

    @commands.cooldown(rate=3, per=20.0, type=commands.BucketType.user)
    @check.acl2(check.ACLevel.EVERYONE)
    @commands.command()
    async def pick(self, ctx, first: str, second: str, *args):
        """Pick an option"""
        args = [first, second, *args]
        for i, arg in enumerate(args):
            if arg.endswith("?"):
                args = args[i + 1 :]
                break

        if len(args) < 2:
            return await ctx.reply(
                _(ctx, "You asked a question, but did not add enough options.")
            )

        option: Optional[str] = utils.text.sanitise(random.choice(args))
        if option is not None:
            await ctx.reply(option)

    @commands.cooldown(rate=3, per=20.0, type=commands.BucketType.user)
    @check.acl2(check.ACLevel.EVERYONE)
    @commands.command()
    async def flip(self, ctx, *, question: Optional[str] = None):
        """Yes/No"""
        choices: List[str] = [_(ctx, "Yes"), _(ctx, "No")]
        await ctx.reply(random.choice(choices))

    @commands.cooldown(rate=5, per=20, type=commands.BucketType.channel)
    @check.acl2(check.ACLevel.EVERYONE)
    @commands.command(aliases=["unsplash"])
    async def picsum(self, ctx, *, seed: Optional[str] = None):
        """Get random image from picsum.photos"""
        size: str = "900/600"
        url: str = "https://picsum.photos/"
        if seed:
            url_seed: str = hashlib.sha3_224(seed.encode("utf-8")).hexdigest()[:16]
            url += "seed/" + url_seed + "/"
        url += f"{size}.jpg?random={ctx.message.id}"

        async with aiohttp.ClientSession(
            headers=self._get_request_headers()
        ) as session, session.get(url) as img_response:
            if img_response.status != 200:
                return await ctx.reply(f"E{img_response.status}")

            image_id: str = str(img_response.url).split("/id/", 1)[1].split("/")[0]
            async with session.get(
                f"https://picsum.photos/id/{image_id}/info"
            ) as response:
                image_info = await response.json()

        try:
            image_url: str = image_info["url"]
        except Exception:
            image_url = None

        footer: str = "picsum.photos"
        if seed:
            footer += f" ({seed})" if len(seed) <= 16 else f" ({seed[:16]}…)"

        embed: discord.Embed = utils.discord.create_embed(
            author=ctx.author,
            description=image_url,
            footer=footer,
        )
        embed.set_image(url=str(img_response.url))

        await ctx.reply(embed=embed)

    @commands.cooldown(rate=5, per=20, type=commands.BucketType.channel)
    @check.acl2(check.ACLevel.EVERYONE)
    @commands.command()
    async def cat(self, ctx):
        """Get random image of a cat"""
        image_response = await self._get_json_from_api(
            "https://api.thecatapi.com/v1/images/search", ctx
        )
        if not image_response:
            return

        fact_response = ""
        if random.randint(0, 9) == 1:
            url: str = "https://meowfacts.herokuapp.com/"
            if TRANSLATOR.get_language_preference(ctx) in ("cs", "sk"):
                url += "?lang=ces"

            fact_response = await self._get_json_from_api(url, ctx, False)
            if not fact_response:
                fact_response = ""
            else:
                fact_response = fact_response["data"][0]
        image_embed: discord.Embed = utils.discord.create_embed(
            author=ctx.author,
            footer="thecatapi.com",
        )
        image_embed.set_image(url=image_response[0]["url"])
        embeds: List[discord.Embed] = [image_embed]

        if fact_response:
            fact_embed = utils.discord.create_embed(
                author=ctx.author,
                title=_(ctx, "Cat fact"),
                description=fact_response,
                footer="meowfacts.herokuapp.com",
            )
            embeds.append(fact_embed)

        await ctx.reply(embeds=embeds)

    @commands.cooldown(rate=5, per=20, type=commands.BucketType.channel)
    @check.acl2(check.ACLevel.EVERYONE)
    @commands.command()
    async def dog(self, ctx):
        """Get random image of a dog"""
        image_response = await self._get_json_from_api(
            "https://api.thedogapi.com/v1/images/search", ctx
        )
        if not image_response:
            return

        fact_response = ""
        if random.randint(0, 9) == 1:
            fact_response = await self._get_json_from_api(
                "https://dogapi.dog/api/facts/", ctx, False
            )
            if not fact_response:
                fact_response = ""
            else:
                fact_response = fact_response["facts"][0]

        image_embed: discord.Embed = utils.discord.create_embed(
            author=ctx.author,
            footer="thedogapi.com",
        )
        image_embed.set_image(url=image_response[0]["url"])
        embeds: List[discord.Embed] = [image_embed]

        if fact_response:
            fact_embed = utils.discord.create_embed(
                author=ctx.author,
                title=_(ctx, "Dog fact"),
                description=fact_response,
                footer="dogfactsapi.ducnguyen.dev",
            )
            embeds.append(fact_embed)

        await ctx.reply(embeds=embeds)

    @commands.cooldown(rate=5, per=20, type=commands.BucketType.channel)
    @check.acl2(check.ACLevel.EVERYONE)
    @commands.command()
    async def fox(self, ctx):
        """Get random image of a fox"""

        json_response = await self._get_json_from_api(
            "https://randomfox.ca/floof/", ctx
        )
        if not json_response:
            return

        embed: discord.Embed = utils.discord.create_embed(
            author=ctx.author,
            footer="randomfox.ca",
        )
        embed.set_image(url=json_response["image"])

        await ctx.reply(embed=embed)

    @commands.cooldown(rate=5, per=20, type=commands.BucketType.channel)
    @check.acl2(check.ACLevel.EVERYONE)
    @commands.command()
    async def duck(self, ctx):
        """Get random image of a duck"""
        json_response = await self._get_json_from_api(
            "https://random-d.uk/api/v2/random", ctx
        )
        if not json_response:
            return

        embed: discord.Embed = utils.discord.create_embed(
            author=ctx.author,
            footer="random-d.uk",
        )
        embed.set_image(url=json_response["url"])

        await ctx.reply(embed=embed)

    @commands.cooldown(rate=5, per=60, type=commands.BucketType.channel)
    @check.acl2(check.ACLevel.EVERYONE)
    @commands.command()
    async def xkcd(self, ctx, number: int = None):
        """Get random xkcd comics

        Arguments
        ---------
        number: Comics number. Omit to get random one.
        """
        # get maximal
        fetched = await self._get_json_from_api("https://xkcd.com/info.0.json", ctx)

        # get random
        if number is None or number < 1 or number > fetched["num"]:
            number: int = random.randint(1, fetched["num"])
        # fetch requested
        if number != fetched["num"]:
            fetched = await self._get_json_from_api(
                f"https://xkcd.com/{number}/info.0.json", ctx
            )

        main_embed: discord.Embed = utils.discord.create_embed(
            author=ctx.author,
            title=fetched["title"],
        )
        main_embed.add_field(
            name=(
                f"{fetched['year']}"
                f"-{str(fetched['month']).zfill(2)}"
                f"-{str(fetched['day']).zfill(2)}"
            ),
            value=(
                f"https://xkcd.com/{number}\n"
                + f"https://www.explainxkcd.com/wiki/index.php/{number}"
            ),
            inline=False,
        )
        main_embed.set_image(url=fetched["img"])
        description_embed: discord.Embed = utils.discord.create_embed(
            author=ctx.author,
            title="_" + _(ctx, "Description") + "_",
            description=fetched["alt"][:2048],
            footer="xkcd.com",
        )

        await ctx.reply(embeds=[main_embed, description_embed])

    @commands.cooldown(rate=5, per=60, type=commands.BucketType.channel)
    @check.acl2(check.ACLevel.EVERYONE)
    @commands.command()
    async def dadjoke(self, ctx, *, keyword: Optional[str] = None):
        """Get random dad joke

        Arguments
        ---------
        keyword: search for a certain keyword in a joke
        """
        if keyword is not None and ("&" in keyword or "?" in keyword):
            return await ctx.reply(_(ctx, "I didn't find a joke like that."))

        params: Dict[str, str] = {"limit": "30"}
        url: str = "https://icanhazdadjoke.com"
        if keyword is not None:
            params["term"] = keyword
            url += "/search"

        fetched = await self._get_json_from_api(url, ctx, params=params)
        if not fetched:
            return

        if keyword is not None:
            res = fetched["results"]
            if len(res) == 0:
                return await ctx.reply(_(ctx, "I didn't find a joke like that."))
            result = random.choice(res)
            result["joke"] = re.sub(
                f"(\\b\\w*{keyword}\\w*\\b)",
                r"**\1**",
                result["joke"],
                flags=re.IGNORECASE,
            )
        else:
            result = fetched

        embed: discord.Embed = utils.discord.create_embed(
            title="Dadjoke",
            author=ctx.author,
            description=result["joke"],
            footer="icanhazdadjoke.com",
            url="https://icanhazdadjoke.com/j/" + result["id"],
        )

        await ctx.reply(embed=embed)

    @commands.cooldown(rate=5, per=60, type=commands.BucketType.channel)
    @check.acl2(check.ACLevel.EVERYONE)
    @commands.command(name="yo-mamma")
    async def yo_mamajoke(self, ctx):
        """Get random Yo mama joke"""
        json_response = await self._get_json_from_api(
            "https://www.yomama-jokes.com/api/v1/jokes/random/", ctx
        )
        if not json_response:
            return

        embed: discord.Embed = utils.discord.create_embed(
            author=ctx.author,
            description=json_response["joke"],
            footer="api.yomomma.info",
        )

        await ctx.reply(embed=embed)

    @commands.cooldown(rate=5, per=60, type=commands.BucketType.channel)
    @check.acl2(check.ACLevel.EVERYONE)
    @commands.command()
    async def joke(self, ctx, *, keyword: Optional[str] = None):
        """Get a random joke

        Arguments
        ---------
        keyword: search for a certain keyword in a joke
        """
        if keyword is not None and ("&" in keyword or "?" in keyword):
            return await ctx.reply(_(ctx, "I didn't find a joke like that."))

        params: Dict[str, str] = {"type": "single"}
        url: str = "https://v2.jokeapi.dev/joke/Any"
        if keyword is not None:
            params["contains"] = urllib.parse.quote(keyword.encode("utf8"))

        result = await self._get_json_from_api(url, ctx, params=params)
        if not result:
            return

        if keyword is not None:
            if result["error"]:
                await ctx.reply(_(ctx, "I didn't find a joke like that."))
                return

            result["joke"] = re.sub(
                f"(\\b\\w*{keyword}\\w*\\b)",
                r"**\1**",
                result["joke"],
                flags=re.IGNORECASE,
            )

        embed: discord.Embed = utils.discord.create_embed(
            author=ctx.author,
            description=result["joke"],
            footer="jokeapi.dev",
        )

        await ctx.reply(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(Rand(bot))
