import discord
from discord.ext import commands

from pie import check, utils, i18n, logger
from modules.base.admin.database import BaseAdminModule
from modules.boards.karma.database import KarmaMember

from .database import Price

_ = i18n.Translator("modules/fun").translate
bot_log = logger.Bot.logger()


class Names(commands.Cog):
    """Pay by karma and I change your name."""

    def __init__(self, bot: commands.Bot):
        # Check if dependency module is loaded.
        if not BaseAdminModule.get("boards.karma").enabled:
            raise Exception(
                "Unable to load names module due to missing module `boards.karma`."
            )

        self.bot = bot

    @commands.bot_has_permissions(manage_nicknames=True)
    @commands.guild_only()
    @check.acl2(check.ACLevel.EVERYONE)
    @commands.cooldown(rate=5, per=20.0, type=commands.BucketType.user)
    @commands.group(name="nickname", aliases=["name"])
    async def nickname_(self, ctx):
        """Change your nickname"""
        await utils.discord.send_help(ctx)

    @commands.guild_only()
    @check.acl2(check.ACLevel.EVERYONE)
    @commands.cooldown(rate=5, per=20.0, type=commands.BucketType.user)
    @nickname_.command(name="prices")
    async def prices(self, ctx):
        """Display prices for various name/nickname operations"""

        embed = utils.discord.create_embed(
            author=ctx.author,
            title=_(ctx, "Change of nickname"),
            description=_(
                ctx,
                "Values are in karma points. Use commnand **nickname/name** for more info.",
            ),
        )
        price = Price.get(ctx.guild.id)
        embed.add_field(
            name=_(ctx, "Set"),
            value=_(ctx, "Price **{price}**").format(
                price=price.set_price if price is not None else _(ctx, "not set")
            ),
        )
        embed.add_field(
            name=_(ctx, "Reset"),
            value=_(ctx, "Price **{price}**").format(
                price=price.reset_price if price is not None else _(ctx, "not set")
            ),
        )

        await ctx.reply(embed=embed)

    @commands.guild_only()
    @check.acl2(check.ACLevel.EVERYONE)
    @commands.cooldown(rate=5, per=20.0, type=commands.BucketType.user)
    @nickname_.command(name="set")
    async def nickname_set(self, ctx, nickname: str):
        """Change server nickname"""
        if not BaseAdminModule.get("boards.karma").enabled:
            await bot_log.error(
                ctx.author,
                ctx.channel,
                "Repository boards.karma is not loaded. Cannot set nickname.",
            )
            await ctx.reply(
                _(ctx, "Cannot change nickname because module karma is not loaded.")
            )
            return

        if nickname == ctx.author.display_name:
            await ctx.reply(
                _(
                    ctx,
                    "New nickname {nickname} is same as current nickname. No need to change.",
                ).format(nickname=nickname)
            )
            return

        price = Price.get(ctx.guild.id)
        if price is None:
            await ctx.reply(
                _(ctx, "Unable to change nickname, this command has no set price.")
            )
            return

        member = KarmaMember.get_or_add(ctx.author.guild.id, ctx.author.id)
        if member.value < price.set_price:
            await ctx.reply(_(ctx, "No enough karma, try to chat more to earn karma."))
            return

        for char in ("@", "#", "`", "'", '"'):
            if char in nickname:
                await ctx.reply(
                    _(ctx, "{nickname} includes some forbidden characters.").format(
                        nickname=nickname
                    )
                )
                return

        try:
            await ctx.author.edit(nick=nickname, reason="Nickname purchase")
        except discord.Forbidden:
            await ctx.reply(
                _(ctx, "Cannot change nickname because you have greater privileges.")
            )
            return

        member.value += -price.set_price
        member.save()

        await ctx.reply(
            _(
                ctx, "Congratulation! You were successfully renamed to {nickname}."
            ).format(nickname=nickname)
        )

    @commands.guild_only()
    @check.acl2(check.ACLevel.EVERYONE)
    @commands.cooldown(rate=5, per=20.0, type=commands.BucketType.user)
    @nickname_.command(name="unset", aliases=["reset"])
    async def nickname_unset(self, ctx):
        """Change your nickname back to global from server"""
        if not BaseAdminModule.get("boards.karma").enabled:
            await bot_log.error(
                ctx.author,
                ctx.channel,
                "Repository boards.karma is not loaded. Cannot reset nickname.",
            )
            await ctx.reply(
                _(ctx, "Cannot change nickname because mudule karma is not loaded.")
            )
            return

        price = Price.get(ctx.guild.id)
        if price is None:
            await ctx.reply(
                _(ctx, "Unable to reset nickname, this command has no set price.")
            )
            return

        member = KarmaMember.get_or_add(ctx.author.guild.id, ctx.author.id)
        if member.value < price.reset_price:
            await ctx.reply(_(ctx, "No enough karma, try to chat more to earn karma."))
            return

        if ctx.author.nick is None:
            await ctx.reply(_(ctx, "You are already using username."))
            return

        try:
            await ctx.author.edit(nick=None, reason="Nickname reset")
        except discord.Forbidden:
            await ctx.reply(
                _(ctx, "Cannot change nickname because you have greater privileges.")
            )
            return

        member.value += -price.reset_price
        member.save()

        await ctx.reply(
            _(ctx, "Congratulation! You are now using username not nickname.")
        )

    @commands.guild_only()
    @check.acl2(check.ACLevel.MOD)
    @commands.cooldown(rate=5, per=20.0, type=commands.BucketType.user)
    @nickname_.command(name="set-prices", aliases=["set_prices"])
    async def nickname_set_prices(self, ctx, set_price: int, reset_price: int):
        """Change prices for set and reset"""
        if set_price < 0 or reset_price < 0:
            await ctx.reply(
                _(
                    ctx,
                    "Unable to change the price because one of the prices have negative value.",
                )
            )
            return
        price = Price.set(ctx.guild.id, set_price, reset_price)
        if price is not None:
            await ctx.reply(_(ctx, "Prices have been successfully updated."))
        else:
            await ctx.reply(_(ctx, "Prices have not been successfully updated."))


async def setup(bot) -> None:
    await bot.add_cog(Names(bot))
