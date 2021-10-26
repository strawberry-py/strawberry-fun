from typing import List

from discord.ext import commands

import database.config
from core import check, i18n, utils

from .database import Seeking as seeking

_ = i18n.Translator("modules/fun").translate
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
        items = seeking.get_all(ctx.guild.id, ctx.channel.id)

        if items:
            template = "#{id} | {name}, {timestamp}"
            for item in items:
                member = ctx.guild.get_member(item.user_id)
                name = (
                    utils.Text.sanitise(member.display_name)
                    if hasattr(member, "display_name")
                    else _(ctx, "Unknown User")
                )
                message_url = f"https://discord.com/channels/{item.guild_id}/{item.channel_id}/{item.message_id}"
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
        """Announce that you're seeking something in under 140 characters
        Arguments
        ---------
        text: Any text in the character limit
        """
        if len(text) > 140:
            return await ctx.reply(
                _(ctx, "The text is too long, you must fit up to 140 characters.")
            )

        seeking.add(
            guild_id=ctx.guild.id,
            channel_id=ctx.channel.id,
            message_id=ctx.message.id,
            user_id=ctx.author.id,
            text=text,
        )
        await ctx.reply(_(ctx, "The item was added."))

    @seeking.command(name="remove")
    async def seeking_remove(self, ctx, *, ids: List[str]):
        """Remove your item
        Arguments
        ---------
        ids: space separated integers
        """
        rejected = []

        for item_id in ids:
            item = seeking.get(ctx.guild.id, ctx.channel.id, item_id)
            if item is None:
                rejected.append(item_id)
                continue

            if item.user_id != ctx.author.id and ctx.author.id != 0:
                rejected.append(item_id)
                continue

            seeking.remove(ctx.guild.id, ctx.channel.id, item_id)

        await ctx.reply(_(ctx, "Done."))
        if len(rejected):
            await ctx.send(
                ", ".join(f"`{utils.Text.sanitise(str(x))}`" for x in rejected[:2000])
            )


def setup(bot) -> None:
    bot.add_cog(Seeking(bot))
