import aiohttp
import random
import re
import hashlib
from typing import Optional, List, Dict

import discord
from discord.ext import commands

from pie import check, utils, i18n

_ = i18n.Translator("modules/fun").translate


class Rand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

        async with aiohttp.ClientSession() as session, session.get(url) as img_response:
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
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.thecatapi.com/v1/images/search"
            ) as response:
                if response.status != 200:
                    await ctx.reply(
                        _(ctx, "Command encountered an error (E{code}).").format(
                            code=response.status
                        )
                    )
                    return

                image_response = await response.json()

            fact_response: str = ""
            if random.randint(0, 9) == 1:
                async with session.get("https://meowfacts.herokuapp.com/") as response:
                    if response.status == 200:
                        fact_response = await response.json()
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
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.thedogapi.com/v1/images/search"
            ) as response:
                if response.status != 200:
                    return await ctx.reply(
                        _(ctx, "Command encountered an error (E{code}).").format(
                            code=response.status
                        )
                    )

                json_response = await response.json()

        embed: discord.Embed = utils.discord.create_embed(
            author=ctx.author,
            footer="thedogapi.com",
        )
        embed.set_image(url=json_response[0]["url"])

        await ctx.reply(embed=embed)

    @commands.cooldown(rate=5, per=20, type=commands.BucketType.channel)
    @check.acl2(check.ACLevel.EVERYONE)
    @commands.command()
    async def fox(self, ctx):
        """Get random image of a fox"""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://randomfox.ca/floof/") as response:
                if response.status != 200:
                    return await ctx.reply(
                        _(ctx, "Command encountered an error (E{code}).").format(
                            code=response.status
                        )
                    )

                json_response = await response.json()

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
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://random-d.uk/api/v2/random?type=jpeg"
            ) as response:
                if response.status != 200:
                    return await ctx.reply(
                        _(ctx, "Command encountered an error (E{code}).").format(
                            code=response.status
                        )
                    )

                json_response = await response.json()

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
        async with aiohttp.ClientSession() as session:
            async with session.get("https://xkcd.com/info.0.json") as response:
                fetched = await response.json()

                # get random
                if number is None or number < 1 or number > fetched["num"]:
                    number: int = random.randint(1, fetched["num"])
                # fetch requested
                if number != fetched["num"]:
                    async with session.get(
                        f"https://xkcd.com/{number}/info.0.json"
                    ) as response:
                        fetched = await response.json()

        embed: discord.Embed = utils.discord.create_embed(
            author=ctx.author,
            title=fetched["title"],
            description="_" + fetched["alt"][:2046] + "_",
            footer="xkcd.com",
        )

        embed.add_field(
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
        embed.set_image(url=fetched["img"])

        await ctx.reply(embed=embed)

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
        headers: Dict[str, str] = {"Accept": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                fetched = await response.json()

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
            author=ctx.author,
            description=result["joke"],
            footer="icanhazdadjoke.com",
            url="https://icanhazdadjoke.com/j/" + result["id"],
        )

        await ctx.reply(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(Rand(bot))
