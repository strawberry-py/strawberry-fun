import argparse
import random
import shlex
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Generator

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

        self._triggers: Dict[int, Dict[str, str]] = {}
        self._refresh_triggers()

    def _refresh_triggers(self):
        triggers = defaultdict(dict)
        for macro in TextMacro.get_all(None):
            # Cached triggers are saved as lowercase.
            # When the message is looked up in the cache, it's also converted
            # to lowercase. This ensures that all macros will be found, even
            # those which are case insensitive.
            macro_triggers = {t.text.lower(): macro.name for t in macro.triggers}
            triggers[macro.guild_id].update(macro_triggers)
        self._triggers = triggers

    #

    @commands.guild_only()
    @check.acl2(check.ACLevel.SUBMOD)
    @commands.group(name="macro")
    async def macro_(self, ctx):
        """Manage automatic bot replies"""
        await utils.discord.send_help(ctx)

    @check.acl2(check.ACLevel.SUBMOD)
    @macro_.command(name="list")
    async def macro_list(self, ctx):
        """List macros defined on this server."""
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

    @check.acl2(check.ACLevel.SUBMOD)
    @macro_.command(name="get")
    async def macro_get(self, ctx, *, name: str):
        """Display full macro details."""
        macro = TextMacro.get(guild_id=ctx.guild.id, name=name)
        if macro is None:
            await ctx.reply(_(ctx, "Macro with that name does not exist."))
            return

        embed = utils.discord.create_embed(
            title=_(ctx, "Macro details: {name}").format(name=name),
            author=ctx.author,
            description=_(ctx, "This macro was run {count} times in total.").format(
                count=macro.counter,
            ),
        )
        embed.add_field(
            name=_(ctx, "Triggers"),
            value="\n".join(m.text for m in macro.triggers),
            inline=False,
        )
        embed.add_field(
            name=_(ctx, "Responses"),
            value="\n".join(m.text for m in macro.responses),
            inline=False,
        )
        embed.add_field(
            name=_(ctx, "Match"),
            value=macro.match.name,
        )
        embed.add_field(
            name=_(ctx, "Case sensitive"),
            value=_(ctx, "Yes") if macro.sensitive else _(ctx, "No"),
        )
        extra: List[str] = []
        if macro.dm:
            extra.append(_(ctx, "Forward to DM"))
        if macro.delete_trigger:
            extra.append(_(ctx, "Delete the trigger"))
        if extra:
            embed.add_field(
                name=_(ctx, "Extra"),
                value="\n".join(extra),
            )

        channels = [ctx.guild.get_channel(c.channel_id) for c in macro.channels]
        channels = [c for c in channels if c is not None]
        if channels:
            embed.add_field(
                name=_(ctx, "Channels"),
                value="\n".join(f"#{c.name}" for c in channels),
                inline=False,
            )
        users = [ctx.guild.get_member(u.user_id) for u in macro.users]
        users = [u for u in users if u is not None]
        if users:
            embed.add_field(
                name=_(ctx, "Users"),
                value="\n".join(utils.text.sanitise(u.display_name) for u in users),
                inline=False,
            )

        await ctx.reply(embed=embed)

    async def _parse_macro_parameters(
        self, ctx: commands.Context, parameters: str
    ) -> Optional[argparse.Namespace]:
        # Some values are 'type=bool', but are being set to None.
        # That's because it messed up updating. When you did not want to update them
        # and omitted them, they ended up overwriting the true intended values in the
        # database.
        # We have to filter these in the '_add()' function because of that.
        try:
            parameters = shlex.split(parameters)
        except Exception as exc:
            raise commands.ArgumentParsingError(str(exc)) from exc

        parser = MacroParser()
        parser.add_argument("--triggers", type=str, nargs="+")
        parser.add_argument("--responses", type=str, nargs="+")
        parser.add_argument("--dm", type=bool, default=None)
        parser.add_argument("--delete-trigger", type=bool, default=None)
        parser.add_argument("--sensitive", type=bool, default=None)
        parser.add_argument("--match", type=str, choices=[m.name for m in MacroMatch])
        parser.add_argument("--channels", type=int, nargs="+")
        parser.add_argument("--users", type=int, nargs="+")
        args = parser.parse_args(parameters)
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
            # disable channel/user overwrites by supplying 0
            if getattr(args, kw) == [0]:
                setattr(args, kw, [])

        return args

    @check.acl2(check.ACLevel.MOD)
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
            --channels: Optional list of channel IDs where this macro will work. Reset by supplying 0.
            --users: Optional list of user IDs for which this macro wil work. Reset by supplying 0.
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
        await guild_log.info(ctx.author, ctx.channel, f"New macro '{name}'.")
        self._refresh_triggers()

    @check.acl2(check.ACLevel.MOD)
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
            --channels: Optional list of channel IDs where this macro will work. Reset by supplying 0.
            --users: Optional list of user IDs for which this macro wil work. Reset by supplying 0.
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
        await guild_log.info(ctx.author, ctx.channel, f"Updated macro '{name}'.")
        self._refresh_triggers()

    @check.acl2(check.ACLevel.MOD)
    @macro_.command(name="remove")
    async def macro_remove(self, ctx, name: str):
        """Remove existing macro."""
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
        if message.guild.id not in self._triggers.keys():
            return None

        content = message.content.lower()

        def get_potential_macros() -> Generator:
            """Get macro name from the message content."""
            for trigger, macro_name in self._triggers[message.guild.id].items():
                if trigger in content:
                    yield macro_name

        for macro_name in get_potential_macros():
            triggered: bool = await self._process_macro(message, macro_name)
            if triggered:
                break

    async def _process_macro(self, message, macro_name: str) -> bool:
        """Process macro.

        Returns:
            True if the macro was triggered, False otherwise.
        """
        macro = TextMacro.get(message.guild.id, macro_name)
        if macro is None:
            await guild_log.error(
                message.author, message.channel, f"Macro '{macro_name}' not found."
            )
            return False
        macro_dump = macro.dump()

        content = message.content
        if not macro.sensitive:
            macro_dump["triggers"] = [t.lower() for t in macro_dump["triggers"]]
            content = content.lower()

        for trigger in macro_dump["triggers"]:
            if macro.match == MacroMatch.FULL and trigger == content:
                break
            if macro.match == MacroMatch.START and content.startswith(trigger):
                break
            if macro.match == MacroMatch.END and content.endswith(trigger):
                break
            if macro.match == MacroMatch.ANY and trigger in content:
                break
        else:
            # the string is contained there, but not precisely
            return False

        # filtering
        if macro.channels and message.channel.id not in macro_dump["channels"]:
            return False
        if macro.users and message.author.id not in macro_dump["users"]:
            return False

        macro.bump()

        # pick one of responses
        response = random.choice(macro_dump["responses"])

        # delete trigger, if set
        if macro.delete_trigger:
            await utils.discord.delete_message(message)

        # send
        if macro.dm:
            await message.author.send(response)
        else:
            await message.reply(response, mention_author=False)
        return True


async def setup(bot) -> None:
    await bot.add_cog(Macro(bot))
