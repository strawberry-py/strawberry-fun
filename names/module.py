import discord
from discord.ext import commands
from modules.base.admin.database import BaseAdminModule
from modules.boards.karma.database import KarmaMember

from pie import check, i18n, logger, utils

from .database import Price

_ = i18n.Translator("modules/fun").translate
bot_log = logger.Bot.logger()
guild_log = logger.Guild.logger()


class Names(commands.Cog):
    """Buy nickname changes for karma points."""

    def __init__(self, bot: commands.Bot):
        # Check if dependency module is loaded.
        if not BaseAdminModule.get("boards.karma").enabled:
            raise Exception(
                "Unable to load names module due to missing module `boards.karma`."
            )

        self.bot = bot

    @commands.bot_has_permissions(manage_nicknames=True)
    @commands.guild_only()
    @check.acl2(check.ACLevel.MEMBER)
    @commands.cooldown(rate=5, per=20.0, type=commands.BucketType.user)
    @commands.group(name="nickname", aliases=["name"])
    async def nickname_(self, ctx):
        """Change your nickname"""
        await utils.discord.send_help(ctx)

    @check.acl2(check.ACLevel.MEMBER)
    @commands.cooldown(rate=5, per=20.0, type=commands.BucketType.user)
    @nickname_.command(name="prices")
    async def prices(self, ctx):
        """Display nickname change prices"""

        embed = utils.discord.create_embed(
            author=ctx.author,
            title=_(ctx, "Nickname change prices"),
            description=_(ctx, "Values are in karma points."),
        )

        price = Price.get(ctx.guild.id)
        embed.add_field(
            name=_(ctx, "Set"),
            value=price.set_price if price is not None else _(ctx, "not set"),
        )
        embed.add_field(
            name=_(ctx, "Reset"),
            value=price.reset_price if price is not None else _(ctx, "not set"),
        )

        await ctx.reply(embed=embed)

    @check.acl2(check.ACLevel.MEMBER)
    @nickname_.command(name="set")
    async def nickname_set(self, ctx, *, nickname: str):
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

        # Strip accidental quotes
        nickname = nickname.strip("'\" ")

        if nickname == ctx.author.display_name:
            await ctx.reply(
                _(ctx, "That nickname is same as current nickname.").format(
                    nickname=nickname
                )
            )
            return

        if nickname in ("everyone", "here", "discord"):
            await ctx.reply(_(ctx, "That nickname is forbidden keyword."))
            return

        for char in ("@", "#", "`", "'", '"'):
            if char in nickname:
                await ctx.reply(
                    _(ctx, "That nickname includes some forbidden characters.").format(
                        nickname=nickname
                    )
                )
                return

        if len(nickname) < 2 or len(nickname) > 32:
            await ctx.reply(
                _(ctx, "The length of a nickname must be between 2 and 32 characters.")
            )
            return

        price = Price.get(ctx.guild.id)
        if price is None:
            await ctx.reply(
                _(ctx, "Unable to change nickname, **set** price not configured.")
            )
            return

        member = KarmaMember.get_or_add(ctx.author.guild.id, ctx.author.id)
        if member.value < price.set_price:
            await ctx.reply(_(ctx, "No enough karma, try to chat more to earn karma."))
            return

        dialog = utils.discord.create_embed(
            author=ctx.author,
            title=_(ctx, "Change server nickname"),
            description=_(
                ctx, "Do you want to change your current nickname to **{nick}**?"
            ).format(nick=utils.text.sanitise(nickname)),
        )
        view = utils.objects.ConfirmView(ctx, dialog)
        view.timeout = 90
        answer = await view.send()
        if answer is not True:
            await ctx.reply(_(ctx, "Your nickname has not been changed."))
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
            _(ctx, "Congratulations, you have been renamed to **{nickname}**.").format(
                nickname=utils.text.sanitise(nickname)
            )
        )
        await guild_log.info(
            ctx.author,
            ctx.channel,
            f"Nickname changed to '{nickname}' for {price.set_price} karma points.",
        )

    @check.acl2(check.ACLevel.MEMBER)
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
                _(ctx, "Cannot change nickname because module karma is not loaded.")
            )
            return

        price = Price.get(ctx.guild.id)
        if price is None:
            await ctx.reply(
                _(ctx, "Unable to change nickname, **unset** price not configured.")
            )
            return

        member = KarmaMember.get_or_add(ctx.author.guild.id, ctx.author.id)
        if member.value < price.reset_price:
            await ctx.reply(_(ctx, "No enough karma, try to chat more to earn karma."))
            return

        if ctx.author.nick is None:
            await ctx.reply(_(ctx, "You have no nickname here."))
            return

        dialog = utils.discord.create_embed(
            author=ctx.author,
            title=_(ctx, "Reset nickname"),
            description=_(ctx, "Do you want to remove your current server nickname?"),
        )
        view = utils.objects.ConfirmView(ctx, dialog)
        view.timeout = 90
        answer = await view.send()
        if answer is not True:
            await ctx.reply(_(ctx, "Your nickname has not been removed."))
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

        await ctx.reply(_(ctx, "Congratulations, your nickname has been removed."))
        await guild_log.info(
            ctx.author,
            ctx.channel,
            f"Nickname reset for {price.reset_price} karma points.",
        )

    @check.acl2(check.ACLevel.MOD)
    @nickname_.command(name="set-prices")
    async def nickname_set_prices(self, ctx, set_price: int, reset_price: int):
        """Change nickname change prices"""
        if set_price < 0 or reset_price < 0:
            await ctx.reply(_(ctx, "Set nor reset price cannot be negative."))
            return

        price = Price.set(ctx.guild.id, set_price, reset_price)
        if price is not None:
            await ctx.reply(_(ctx, "Prices have been successfully updated."))
        else:
            await ctx.reply(_(ctx, "Prices have not been successfully updated."))


async def setup(bot) -> None:
    await bot.add_cog(Names(bot))
