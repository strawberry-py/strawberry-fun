import contextlib

from nextcord.ext import commands

import database.config
from core import check, i18n, logger, utils

from .database import Seeking as SeekingDB

_ = i18n.Translator("modules/fun").translate
guild_log = logger.Guild.logger()
config = database.config.Config.get()


class Seeking(commands.Cog):
    """Look for... stuff"""

    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @commands.check(check.acl)
    @commands.group(name="seeking")
    async def seeking(self, ctx):
        """List items for current channel"""
        if ctx.invoked_subcommand is not None:
            return

        embed = utils.Discord.create_embed(
            author=ctx.author,
            title=_(ctx, "Seeking"),
        )
        items = SeekingDB.get_all(ctx.guild.id, ctx.channel.id)

        if items:
            template = "#{id} | {name}, {timestamp}"
            for item in items:
                member = ctx.guild.get_member(item.user_id)
                name = (
                    utils.Text.sanitise(member.display_name)
                    if hasattr(member, "display_name")
                    else _(ctx, "Unknown User")
                )
                message_url: str = (
                    f"https://discord.com/channels/{item.guild_id}/"
                    f"{item.channel_id}/{item.message_id}"
                )
                text = f"{item.text} | [link]({message_url})"
                timestamp = utils.Time.id_to_datetime(item.message_id)
                embed.add_field(
                    name=template.format(
                        id=item.idx,
                        name=name,
                        timestamp=utils.Time.datetime(timestamp),
                    ),
                    value=text,
                    inline=False,
                )
        else:
            embed.add_field(name="\u200b", value=_(ctx, "No items found"))
        await ctx.send(embed=embed)

    @seeking.command(name="add")
    async def seeking_add(self, ctx, *, text: str):
        """Announce that you're seeking something in under 140 characters"""
        if len(text) > 140:
            await ctx.reply(
                _(ctx, "The text is too long, the limit is 140 characters.")
            )
            return

        item = SeekingDB.add(
            guild_id=ctx.guild.id,
            channel_id=ctx.channel.id,
            message_id=ctx.message.id,
            user_id=ctx.author.id,
            text=text,
        )
        await ctx.reply(_(ctx, "The item was added as #{idx}.").format(idx=item.idx))
        await guild_log.info(ctx.author, ctx.channel, f"New seeking item #{item.idx}.")

    @seeking.command(name="remove")
    async def seeking_remove(self, ctx, *, ids: str):
        """Remove seeked items

        :param ids: Space separated list of item IDs.
        """
        for idx in ids.split(" "):
            with contextlib.suppress(ValueError):
                idx = int(idx)
            item = SeekingDB.get(ctx.guild.id, ctx.channel.id, idx)
            if item is None:
                await ctx.reply(_(ctx, "Item #{idx} does not exist.").format(idx=idx))
                return

            if item.user_id != ctx.author.id:
                await ctx.reply(
                    _(ctx, "You don't have permission to remove #{idx}.").format(
                        idx=idx
                    )
                )
                return

        for idx in ids:
            SeekingDB.remove(ctx.guild.id, ctx.channel.id, int(idx))

        if len(ids) == 1:
            await ctx.reply(_(ctx, "The item was deleted."))
        else:
            await ctx.reply(_(ctx, "All items were deleted."))

        await guild_log.info(ctx.author, ctx.channel, f"Seeking items deleted: {ids}.")


def setup(bot) -> None:
    bot.add_cog(Seeking(bot))
