import argparse
import shlex
from collections import defaultdict
from typing import Any, Dict, Set, Optional, Iterable

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

        self._triggers: Dict[int, Set[str]] = {}
        self._refresh_triggers()

    def _refresh_triggers(self):
        triggers = defaultdict(set)
        for macro in TextMacro.get_all(None):
            macro_triggers = [t.text for t in macro.triggers]
            triggers[macro.guild_id].union(*macro_triggers)
        self._triggers = triggers

    #

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

    async def _parse_macro_parameters(
        self, ctx: commands.Context, parameters: str
    ) -> Optional[argparse.Namespace]:
        # Some values are 'type=bool', but are being set to None.
        # That's because it messed up updating. When you did not want to update them
        # and omitted them, they ended up overwriting the true intended values in the
        # database.
        # We have to filter these in the '_add()' function because of that.
        parser = MacroParser()
        parser.add_argument("--triggers", type=str, nargs="+")
        parser.add_argument("--responses", type=str, nargs="+")
        parser.add_argument("--dm", type=bool, default=None)
        parser.add_argument("--delete-trigger", type=bool, default=None)
        parser.add_argument("--sensitive", type=bool, default=None)
        parser.add_argument("--match", type=str, choices=[m.name for m in MacroMatch])
        parser.add_argument("--channels", type=int, nargs="?")
        parser.add_argument("--users", type=int, nargs="?")
        args = parser.parse_args(shlex.split(parameters))
        if parser.error_message:
            await ctx.reply(
                _(ctx, "Macro could not be added:")
                + f"\n> `{parser.error_message.replace('`', '')}`"
            )
            return None

        # Ensure that everything is the right data type.
        # argparse does not have clear way to specify that we want to have lists
        # of some data types, this is the cleanest way. It does not support
        # typing.* types, unfortunately.
        for kw in ("triggers", "responses"):
            if getattr(args, kw).__class__ is str:
                setattr(args, kw, [getattr(args, kw)])
        for kw in ("channels", "users"):
            if getattr(args, kw).__class__ is int:
                setattr(args, kw, [getattr(args, kw)])

        return args

    @commands.check(check.acl)
    @macro_.command(name="add")
    async def macro_add(self, ctx, name: str, *, parameters: str):
        """Add new macro.

        Args:
            --triggers: Trigger phrases.
            --responses: Possible answers; one of them will be picked each time.
            --dm: Whether to send the reply to DM instead of the trigger channel; defaults to False.
            --delete-trigger: Whether to delete the trigger message; defaults to False.
            --sensitive: Case-sensitivity; defaults to False.
            --match: One of FULL, START, END, ANY.
            --channels: Optional list of channel IDs where this macro will work.
            --users: Optional list of user IDs for which this macro wil work.
        """
        if TextMacro.get(guild_id=ctx.guild.id, name=name):
            await ctx.reply(_(ctx, "Macro with that name already exists."))
            return

        args = await self._parse_macro_parameters(ctx, parameters)
        if args is None:
            return

        for arg in ("match", "triggers", "responses"):
            if not getattr(args, arg, None):
                await ctx.reply(
                    _(ctx, "Argument --{arg} must be specified.").format(arg=arg)
                )
                return

        TextMacro.add(
            guild_id=ctx.guild.id,
            name=name,
            triggers=args.triggers,
            responses=args.responses,
            dm=args.dm if args.dm is not None else False,
            delete_trigger=args.delete_trigger
            if args.delete_trigger is not None
            else False,
            sensitive=args.sensitive if args.sensitive is not None else False,
            match=getattr(MacroMatch, args.match.upper()),
            channels=args.channels if args.users.__class__ is int else args.channels,
            users=[args.users] if args.users.__class__ is int else args.users,
        )

        await ctx.reply(_(ctx, "Macro **{name}** created.").format(name=name))
        await guild_log.info(
            ctx.author, ctx.channel, f"New {args.match}-matched macro '{name}'."
        )
        self._refresh_triggers()

    @commands.check(check.acl)
    @macro_.command(name="update")
    async def macro_update(self, ctx, name: str, *, parameters: str):
        """Update existing macro.

        Only include the arguments you want to change.

        Args:
            --triggers: Trigger phrases.
            --responses: Possible answers; one of them will be picked each time.
            --dm: Whether to send the reply to DM instead of the trigger channel; defaults to False.
            --delete-trigger: Whether to delete the trigger message; defaults to False.
            --sensitive: Case-sensitivity; defaults to False.
            --match: One of FULL, START, END, ANY.
            --channels: Optional list of channel IDs where this macro will work.
            --users: Optional list of user IDs for which this macro wil work.
        """
        macro = TextMacro.get(guild_id=ctx.guild.id, name=name)
        if not macro:
            await ctx.reply(_(ctx, "Macro with that name does not exist."))
            return

        args = await self._parse_macro_parameters(ctx, parameters)
        if args is None:
            return

        filtered_args: Dict[str, Any] = {}
        for arg in (
            "triggers",
            "responses",
            "dm",
            "delete_trigger",
            "sensitive",
            "match",
            "channels",
            "users",
        ):
            if getattr(args, arg, None) is not None:
                filtered_args[arg] = getattr(args, arg)

        if not filtered_args:
            await ctx.reply(_(ctx, "No arguments specified."))
            return

        macro.update(**filtered_args)

        await ctx.reply(_(ctx, "Macro **{name}** updated.").format(name=name))
        await guild_log.info(
            ctx.author, ctx.channel, f"Updated {args.match}-matched macro '{name}'."
        )
        self._refresh_triggers()

    @commands.check(check.acl)
    @macro_.command(name="remove")
    async def macro_remove(self, ctx, name: str):
        removed: int = TextMacro.remove(ctx.guild.id, name)

        if removed == 0:
            await ctx.reply(_(ctx, "Macro with that name does not exist."))
            return

        await ctx.reply(_(ctx, "Macro **{name}** removed.").format(name=name))
        await guild_log.info(ctx.author, ctx.channel, f"Removed macro '{name}'.")
        self._refresh_triggers()

    #

    @commands.Cog.listener()
    async def on_message(self, message: str):
        if message.author.bot:
            return

        def has_trigger(message):
            if message.guild.id not in self._triggers.keys():
                return False
            for trigger in self._triggers[message.guild.id]:
                if trigger in message.content:
                    return True
            return False

        if not has_trigger(message):
            return


def setup(bot) -> None:
    bot.add_cog(Macro(bot))
