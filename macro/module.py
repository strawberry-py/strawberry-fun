import argparse
import shlex
from typing import Optional, Iterable

from discord.ext import commands

from pie import check, i18n, logger, utils

from .database import TextMacro, MacroMatch

_ = i18n.Translator("modules/fun").translate
guild_log = logger.Guild.logger()


class MacroParser(argparse.ArgumentParser):
    """Patch ArgumentParser.

    ArgumentParser calls sys.exit(2) on incorrect command,
    which would take down the bot. This subclass catches the errors
    and saves them in 'error_message' attribute.
    """

    error_message: Optional[str] = None

    def error(self, message: str):
        """Save the error message."""
        self.error_message = message

    def exit(self):
        """Make sure the program _does not_ exit."""
        pass

    def parse_args(self, args: Iterable):
        """Catch exceptions that do not occur when CLI program exits."""
        returned = self.parse_known_args(args)
        try:
            args, argv = returned
        except TypeError:
            # There was an error and it is saved in 'error_message'
            return None
        return args


class Macro(commands.Cog):
    """Automatic bot replies"""

    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @commands.check(check.acl)
    @commands.group(name="macro")
    async def macro_(self, ctx):
        """Manage automatic bot replies"""
        await utils.discord.send_help(ctx)

    @commands.check(check.acl)
    @macro_.command(name="list")
    async def macro_list(self, ctx):
        macros = TextMacro.get_all(ctx.guild.id)
        if not macros:
            await ctx.reply(_(ctx, "This server does not have defined any macros."))
            return

        class Item:
            def __init__(self, macro: TextMacro):
                self.name = macro.name
                self.match = macro.match.name
                self.counter = macro.counter
                self.triggers = "|".join(t.text for t in macro.triggers)

        table = utils.text.create_table(
            [Item(m) for m in macros],
            {
                "name": _(ctx, "Macro name"),
                "match": _(ctx, "Match"),
                "counter": _(ctx, "Invocations"),
                "triggers": _(ctx, "Triggers"),
            },
        )
        for page in table:
            await ctx.send("```" + page + "```")

    @commands.check(check.acl)
    @macro_.command(name="add")
    async def macro_add(self, ctx, name: str, *, text: str):
        """Add new macro.

        Args:
            --triggers: Trigger phrases.
            --responses: Possible answers; one of them will be picked each time.
            --sensitive: Case-sensitivity; defaults to False.
            --match: One of FULL, START, END, ANY.
            --channels: Optional list of channel IDs where this macro will work.
            --users: Optional list of users for which this macro wil work.
        """
        parser = MacroParser()
        parser.add_argument("--triggers", type=str, nargs="+", required=True)
        parser.add_argument("--responses", type=str, nargs="+", required=True)
        parser.add_argument("--sensitive", type=bool, default=False)
        parser.add_argument(
            "--match", type=str, choices=[m.name for m in MacroMatch], required=True
        )
        parser.add_argument("--channels", type=int, nargs="?")
        parser.add_argument("--users", type=int, nargs="?")
        args = parser.parse_args(shlex.split(text))
        if parser.error_message:
            await ctx.reply(
                _(ctx, "Macro could not be added:")
                + f"\n> `{parser.error_message.replace('`', '')}`"
            )
            return

        for arg in ("match", "triggers", "responses"):
            if not getattr(args, arg, None):
                await ctx.reply(
                    _(ctx, "Argument --{arg} must be specified.").format(arg=arg)
                )
                return

        if TextMacro.get(guild_id=ctx.guild.id, name=name):
            await ctx.reply(_(ctx, "Macro with that name already exists."))
            return

        TextMacro.add(
            guild_id=ctx.guild.id,
            name=name,
            triggers=args.triggers,
            responses=args.responses,
            sensitive=args.sensitive,
            match=getattr(MacroMatch, args.match.upper()),
            channels=args.channels,
            users=args.users,
        )

        await ctx.reply(_(ctx, "Macro **{name}** created.").format(name=name))
        await guild_log.info(
            ctx.author, ctx.channel, f"New {args.match}-matched macro {name}."
        )

    @commands.check(check.acl)
    @macro_.command(name="update")
    async def macro_update(self, ctx, name: str):
        pass

    @commands.check(check.acl)
    @macro_.command(name="remove")
    async def macro_remove(self, ctx, name: str):
        pass


def setup(bot) -> None:
    bot.add_cog(Macro(bot))
