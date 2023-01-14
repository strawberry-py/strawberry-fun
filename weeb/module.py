import aiohttp
from typing import Optional

import discord
from discord.ext import commands
from discord.abc import PrivateChannel

from pie import check, utils, i18n
from .database import Details

_ = i18n.Translator("modules/fun").translate


class Weeb(commands.Cog):
    """Weeby commands for your own Weebiness"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @classmethod
    def doujin_tags(cls, ctx, dic):
        tag_names = {
            "character": _(ctx, "Characters"),
            "parody": _(ctx, "Parodies"),
            "tag": _(ctx, "Tags"),
            "artist": _(ctx, "Artists"),
            "group": _(ctx, "Groups"),
            "language": _(ctx, "Languages"),
            "category": _(ctx, "Categories"),
        }

        tags: dict[str, list[str]] = {}
        for key in tag_names.keys():
            tags[key] = []
        for tag in dic["tags"]:
            tags[tag["type"]].append(tag["name"])

        result: dict[str, str] = {}
        for tag, tag_name in tag_names.items():
            result[tag_name] = ", ".join(tags[tag])

        return result

    def embed(self, ctx, dic, doujin_id):
        tags = self.doujin_tags(ctx, dic)

        url = f"https://nhentai.net/g/{doujin_id}/"

        if dic["images"]["pages"][0]["t"] == "j":
            cover_url = f"https://i.nhentai.net/galleries/{dic['media_id']}/1.jpg"
        elif dic["images"]["pages"][0]["t"] == "p":
            cover_url = f"https://i.nhentai.net/galleries/{dic['media_id']}/1.png"

        title = dic["title"]["pretty"]
        num_pages = dic["num_pages"]

        embed: discord.Embed = utils.discord.create_embed(
            author=ctx.message.author,
            title=title,
            url=url,
            color=discord.Colour.from_rgb(227, 47, 86),
        )
        embed.set_image(url=cover_url)
        embed.add_field(name=_(ctx, "Number of pages"), value=num_pages, inline=True)

        for typ, tag in tags.items():
            if tag != "":
                if typ == "Tags":
                    embed.add_field(name=typ, value=tag, inline=False)
                else:
                    embed.add_field(name=typ, value=tag, inline=True)
        return embed

    def is_channel_weeby(self, message):
        if isinstance(message.channel, PrivateChannel):
            return True
        if message.channel.is_nsfw:
            return True
        return False

    @commands.guild_only()
    @check.acl2(check.ACLevel.MEMBER)
    @commands.cooldown(rate=5, per=20.0, type=commands.BucketType.user)
    @commands.command()
    async def sauce(self, ctx, doujin_id: Optional[int] = None):
        """Give a magic number and you will get your sauce"""

        if not self.is_channel_weeby(ctx.message):
            raise commands.MissingPermissions
        else:
            if not doujin_id:
                await ctx.send(
                    ">>> "
                    + _(
                        ctx,
                        "Supply me with a magic number and I will give you what you desire.",
                    )
                )
                return
            async with ctx.typing():
                try:
                    details = Details.get(ctx.guild.id)
                    if details is None:
                        return await ctx.reply(
                            _(
                                ctx,
                                "The request will fail because user-agent and cf_clearance cookie is not set.",
                            )
                        )
                    headers = {
                        "User-Agent": details.user_agent,
                        "cookie": "cf_clearance=" + details.cf_clearance,
                    }

                    async with aiohttp.ClientSession(headers=headers) as session:
                        async with session.get(
                            f"https://nhentai.net/api/gallery/{doujin_id}"
                        ) as response:
                            if response.status != 200:
                                return await ctx.reply(
                                    _(
                                        ctx, "Command encountered an error (E{code})."
                                    ).format(code=response.status)
                                )
                            dic = await response.json()
                            response.close()
                except Exception as err:
                    await ctx.send(f"Error occured: {err}")
                else:
                    # successful aiohttp request
                    embed = self.embed(ctx, dic, doujin_id)

            await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if "omae wa mou shindeiru" in message.content.lower():
            await message.channel.send("NANI")

    @commands.guild_only()
    @check.acl2(check.ACLevel.MOD)
    @commands.command(name="weeb-set-connection")
    async def weeb_set_connection_details(
        self, ctx, user_agent: str, cf_clearance: str
    ):
        """Change connection user-agent and cf_clearance cookie for sauce command. These details must be from same session."""
        details = Details.set(ctx.guild.id, user_agent, cf_clearance)
        if details is not None:
            await ctx.reply(
                _(ctx, "Connection details have been successfully updated.")
            )
        else:
            await ctx.reply(
                _(ctx, "Connection details have not been successfully updated.")
            )


async def setup(bot) -> None:
    await bot.add_cog(Weeb(bot))
