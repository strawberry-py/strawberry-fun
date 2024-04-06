import aiohttp
import asyncio
import contextlib
import random
from io import BytesIO
from typing import List, Set, Tuple, Optional, Union
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import discord
from discord.ext import commands

import pie.database.config
from pie import check, logger, utils, i18n

from .database import Relation, RelationOverwrite
from .image_utils import ImageUtils

_ = i18n.Translator("modules/fun").translate
config = pie.database.config.Config.get()
bot_log = logger.Bot.logger()
guild_log = logger.Guild.logger()


DATA_DIR = Path(__file__).parent / "data"
ACTIONS = (
    "hug",
    "pet",
    "hyperpet",
    "highfive",
    "spank",
    "slap",
    "bonk",
    "whip",
    "lick",
    "hyperlick",
)
ACTION_VARIANTS = {
    "spank": ["default", "figures"],
}
EMBED_LIST_LIMIT: int = 5


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.pending_highfives: Set[Tuple[int, int]] = {*()}
        self.pending_hugs: Set[Tuple[int, int]] = {*()}

    @commands.guild_only()
    @commands.cooldown(rate=2, per=10.0, type=commands.BucketType.user)
    @check.acl2(check.ACLevel.MEMBER)
    @commands.command()
    async def hug(self, ctx, *, user: Union[discord.Member, discord.Role] = None):
        """Hug someone"""
        if not await self._is_user_in_channel(ctx, user):
            await ctx.reply(_(ctx, "You can't do that, they are not in this channel."))
            return

        if user is None:
            source = self.bot.user
            target = ctx.author
        else:
            source = ctx.author
            target = user

        if type(target) is discord.Role:
            Relation.add(ctx.guild.id, source.id, None, "hug")
        else:
            Relation.add(ctx.guild.id, source.id, target.id, "hug")

        border: str = "***" if type(target) is discord.Role else "**"

        source_name: str = utils.text.sanitise(source.display_name)
        if type(target) is discord.Member:
            target_name: str = utils.text.sanitise(target.display_name)
        else:
            target_name: str = utils.text.sanitise(target.name)

        hug_face = random.choices(
            ["・ᴗ・", "・⌣・", "・≧▽≦・", "・‿‿・", "・﹏・", "◕‿‿◕", "▀̿_▀̿", "´▽｀"],
            weights=(91, 1, 1, 1, 1, 1, 1, 1),
        )[0]
        if (target.id, source.id) not in self.pending_hugs:
            hug_emoji: str = f"(⊃{hug_face})⊃"
            message: str = f"{hug_emoji} {border}{target_name}{border}"
        else:
            hug_emoji: str = rf"(つˆ⌣ˆ)つ⊂({hug_face}⊂)"
            message: str = (
                f"{border}{source_name}{border} "
                f"{hug_emoji} "
                f"{border}{target_name}{border}"
            )

        await ctx.send(message)
        self.pending_hugs.add((source.id, target.id))
        await asyncio.sleep(20)
        with contextlib.suppress(KeyError):
            self.pending_hugs.remove((source.id, target.id))

    @commands.guild_only()
    @commands.cooldown(rate=2, per=10.0, type=commands.BucketType.user)
    @check.acl2(check.ACLevel.MEMBER)
    @commands.command()
    async def highfive(self, ctx, *, user: discord.Member):
        """Highfive someone

        The user has to highfive you in under twenty seconds.
        """
        if not await self._is_user_in_channel(ctx, user):
            await ctx.reply(_(ctx, "You can't do that, they are not in this channel."))
            return

        source = ctx.author
        target = user
        target_name: str = utils.text.sanitise(target.display_name)
        source_name: str = utils.text.sanitise(source.display_name)

        if (target.id, source.id) not in self.pending_highfives:
            self.pending_highfives.add((source.id, target.id))
            await asyncio.sleep(20)
            try:
                self.pending_highfives.remove((source.id, target.id))
            except KeyError:
                # This failed, that means that the highfive was sucessful.
                return
            else:
                # Highfive failed
                await ctx.author.send(
                    _(
                        ctx,
                        "**{user}** did not highfive you back on time in #{channel}.",
                    ).format(user=target_name, channel=ctx.channel.name)
                )
                return

        with contextlib.suppress(KeyError):
            self.pending_highfives.remove((target.id, source.id))

        # This is 'highfive-back' branch, the current target is the original initiator
        Relation.add(ctx.guild.id, target.id, source.id, "highfive")

        await ctx.send(f"**{target_name}** 人 **{source_name}**")

    @commands.guild_only()
    @commands.cooldown(rate=3, per=30.0, type=commands.BucketType.user)
    @check.acl2(check.ACLevel.MEMBER)
    @commands.command()
    async def whip(self, ctx, *, user: discord.Member = None):
        """Whip someone"""
        if not await self._is_user_in_channel(ctx, user):
            await ctx.reply(_(ctx, "You can't do that, they are not in this channel."))
            return

        if user is None:
            source = self.bot.user
            target = ctx.author
        else:
            source = ctx.author
            target = user

        Relation.add(ctx.guild.id, source.id, target.id, "whip")

        async with ctx.typing():
            avatar: Image = await self.get_users_avatar(ctx, target)

            frames = self.get_whip_frames(avatar)

            with BytesIO() as image_binary:
                frames[0].save(
                    image_binary,
                    format="GIF",
                    save_all=True,
                    append_images=frames[1:],
                    duration=30,
                    loop=0,
                    transparency=0,
                    disposal=2,
                    optimize=False,
                )
                image_binary.seek(0)
                await ctx.reply(
                    file=discord.File(fp=image_binary, filename="whip.gif"),
                    mention_author=False,
                )

    @commands.guild_only()
    @commands.cooldown(rate=3, per=30.0, type=commands.BucketType.user)
    @check.acl2(check.ACLevel.MEMBER)
    @commands.command()
    async def spank(self, ctx, *, user: discord.Member = None):
        """Spank someone"""
        if not await self._is_user_in_channel(ctx, user):
            await ctx.reply(_(ctx, "You can't do that, they are not in this channel."))
            return

        if user is None:
            source = self.bot.user
            target = ctx.author
        else:
            source = ctx.author
            target = user

        Relation.add(ctx.guild.id, source.id, target.id, "spank")

        async with ctx.typing():
            source_avatar: Image = await self.get_users_avatar(ctx, source)
            target_avatar: Image = await self.get_users_avatar(ctx, target)

            frame_duration: int = 30
            variant = getattr(
                RelationOverwrite.get(ctx.guild.id, ctx.channel.id, "spank"),
                "variant",
                "default",
            )
            if variant == "figures":
                frames = self.get_spank_frames_figures(source_avatar, target_avatar)
                frame_duration = 200
            else:
                frames = self.get_spank_frames(target_avatar)

            with BytesIO() as image_binary:
                frames[0].save(
                    image_binary,
                    format="GIF",
                    save_all=True,
                    append_images=frames[1:],
                    duration=frame_duration,
                    loop=0,
                    transparency=0,
                    disposal=2,
                    optimize=False,
                )
                image_binary.seek(0)
                await ctx.reply(
                    file=discord.File(fp=image_binary, filename="spank.gif"),
                    mention_author=False,
                )

    @commands.guild_only()
    @commands.cooldown(rate=3, per=30.0, type=commands.BucketType.user)
    @check.acl2(check.ACLevel.MEMBER)
    @commands.command()
    async def pet(self, ctx, *, user: discord.Member = None):
        """Pet someone"""
        if not await self._is_user_in_channel(ctx, user):
            await ctx.reply(_(ctx, "You can't do that, they are not in this channel."))
            return

        if user is None:
            source = self.bot.user
            target = ctx.author
        else:
            source = ctx.author
            target = user

        Relation.add(ctx.guild.id, source.id, target.id, "pet")

        async with ctx.typing():
            avatar: Image = await self.get_users_avatar(ctx, target)

            frames = self.get_pet_frames(avatar)

            with BytesIO() as image_binary:
                frames[0].save(
                    image_binary,
                    format="GIF",
                    save_all=True,
                    append_images=frames[1:],
                    duration=40,
                    loop=0,
                    transparency=0,
                    disposal=2,
                    optimize=False,
                )
                image_binary.seek(0)
                await ctx.reply(
                    file=discord.File(fp=image_binary, filename="pet.gif"),
                    mention_author=False,
                )

    @commands.guild_only()
    @commands.cooldown(rate=3, per=30.0, type=commands.BucketType.user)
    @check.acl2(check.ACLevel.MEMBER)
    @commands.command()
    async def hyperpet(self, ctx, *, user: discord.Member = None):
        """Hyperpet someone"""
        if not await self._is_user_in_channel(ctx, user):
            await ctx.reply(_(ctx, "You can't do that, they are not in this channel."))
            return

        if user is None:
            source = self.bot.user
            target = ctx.author
        else:
            source = ctx.author
            target = user

        Relation.add(ctx.guild.id, source.id, target.id, "hyperpet")

        async with ctx.typing():
            avatar: Image = await self.get_users_avatar(ctx, target)

            frames = self.get_hyperpet_frames(avatar)

            with BytesIO() as image_binary:
                frames[0].save(
                    image_binary,
                    format="GIF",
                    save_all=True,
                    append_images=frames[1:],
                    duration=30,
                    loop=0,
                    transparency=0,
                    disposal=2,
                    optimize=False,
                )
                image_binary.seek(0)
                await ctx.reply(
                    file=discord.File(fp=image_binary, filename="hyperpet.gif"),
                    mention_author=False,
                )

    @commands.guild_only()
    @commands.cooldown(rate=3, per=30.0, type=commands.BucketType.user)
    @check.acl2(check.ACLevel.MEMBER)
    @commands.command()
    async def bonk(self, ctx, *, user: discord.Member = None):
        """Bonk someone

        member: Discord user. If none, the bot will bonk you.
        """
        if not await self._is_user_in_channel(ctx, user):
            await ctx.reply(_(ctx, "You can't do that, they are not in this channel."))
            return

        if user is None:
            source = self.bot.user
            target = ctx.author
        else:
            source = ctx.author
            target = user

        Relation.add(ctx.guild.id, source.id, target.id, "bonk")

        async with ctx.typing():
            avatar: Image = await self.get_users_avatar(ctx, target)

            frames = self.get_bonk_frames(avatar)

            with BytesIO() as image_binary:
                frames[0].save(
                    image_binary,
                    format="GIF",
                    save_all=True,
                    append_images=frames[1:],
                    duration=30,
                    loop=0,
                    transparency=0,
                    disposal=2,
                    optimize=False,
                )
                image_binary.seek(0)
                await ctx.reply(
                    file=discord.File(fp=image_binary, filename="bonk.gif"),
                    mention_author=False,
                )

    @commands.guild_only()
    @commands.cooldown(rate=3, per=30.0, type=commands.BucketType.user)
    @check.acl2(check.ACLevel.MEMBER)
    @commands.command()
    async def slap(self, ctx, *, user: Union[discord.Member, discord.Role] = None):
        """Slap someone"""
        if not await self._is_user_in_channel(ctx, user):
            await ctx.reply(_(ctx, "You can't do that, they are not in this channel."))
            return

        if user is None:
            source = self.bot.user
            target = ctx.author
        else:
            source = ctx.author
            target = user

        options = ["つ", "づ", "ノ"]

        target_name: str
        border: str
        if type(target) is discord.Role:
            Relation.add(ctx.guild.id, source.id, None, "slap")
            target_name = target.name
            border = "***"
        else:
            Relation.add(ctx.guild.id, source.id, target.id, "slap")
            target_name = target.display_name
            border = "**"

        await ctx.reply(
            "{source} {slap} {border}{target}{border}".format(
                source=utils.text.sanitise(source.display_name),
                slap=random.choice(options),
                border=border,
                target=utils.text.sanitise(target_name),
            ),
            mention_author=False,
        )

    @commands.guild_only()
    @commands.cooldown(rate=5, per=60.0, type=commands.BucketType.user)
    @check.acl2(check.ACLevel.MEMBER)
    @commands.command()
    async def lick(self, ctx, *, user: discord.Member = None):
        """Lick someone"""
        if not await self._is_user_in_channel(ctx, user):
            await ctx.reply(_(ctx, "You can't do that, they are not in this channel."))
            return

        if user is None:
            source = self.bot.user
            target = ctx.author
        else:
            source = ctx.author
            target = user

        Relation.add(ctx.guild.id, source.id, target.id, "lick")

        async with ctx.typing():
            avatar: Image = await self.get_users_avatar(ctx, target)

            frames = self.get_lick_frames(avatar)

            with BytesIO() as image_binary:
                frames[0].save(
                    image_binary,
                    format="GIF",
                    save_all=True,
                    append_images=frames[1:],
                    duration=30,
                    loop=0,
                    transparency=0,
                    disposal=2,
                    optimize=False,
                )
                image_binary.seek(0)
                await ctx.reply(
                    file=discord.File(fp=image_binary, filename="lick.gif"),
                    mention_author=False,
                )

    @commands.guild_only()
    @commands.cooldown(rate=5, per=60.0, type=commands.BucketType.user)
    @check.acl2(check.ACLevel.MEMBER)
    @commands.command()
    async def hyperlick(self, ctx, *, user: discord.Member = None):
        """Hyperlick someone"""
        if not await self._is_user_in_channel(ctx, user):
            await ctx.reply(_(ctx, "You can't do that, they are not in this channel."))
            return

        if user is None:
            source = self.bot.user
            target = ctx.author
        else:
            source = ctx.author
            target = user

        Relation.add(ctx.guild.id, source.id, target.id, "hyperlick")

        async with ctx.typing():
            avatar: Image = await self.get_users_avatar(ctx, target)

            frames = self.get_hyperlick_frames(avatar)

            with BytesIO() as image_binary:
                frames[0].save(
                    image_binary,
                    format="GIF",
                    save_all=True,
                    append_images=frames[1:],
                    duration=30,
                    loop=0,
                    transparency=0,
                    disposal=2,
                    optimize=False,
                )
                image_binary.seek(0)
                await ctx.reply(
                    file=discord.File(fp=image_binary, filename="hyperlick.gif"),
                    mention_author=False,
                )

    @commands.guild_only()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @check.acl2(check.ACLevel.MEMBER)
    @commands.command()
    async def relations(self, ctx, *, user: discord.User = None):
        """Get your information about hugs, pets, ..."""
        if user is None:
            user = ctx.author

        embed = utils.discord.create_embed(
            author=ctx.author,
            title=_(ctx, "Relations {name}").format(
                name=utils.text.sanitise(user.display_name)
            ),
            description=_(ctx, "gave / got"),
        )

        for action in ACTIONS:
            action_stats = Relation.get_user_relation(ctx.guild.id, user.id, action)

            if action_stats[0] == 0 and action_stats[1] == 0:
                continue

            embed.add_field(
                name=action,
                value=f"{action_stats[0]} / {action_stats[1]}",
            )

        action_embeds: List[discord.Embed] = [
            Fun.get_action_embed(ctx, user, action) for action in ACTIONS
        ]
        embeds: List[discord.Embed] = [embed] + [
            e for e in action_embeds if e is not None
        ]

        avatar_url: str = user.display_avatar.replace(size=256).url
        embeds = [e.set_thumbnail(url=avatar_url) for e in embeds]

        scollable = utils.ScrollableEmbed(ctx, embeds)
        await scollable.scroll()

    @check.acl2(check.ACLevel.MEMBER)
    @commands.command(aliases=["owo"])
    async def uwu(self, ctx, *, message: str = None):
        """UWUize message"""
        if message is None:
            text = "OwO!"
        else:
            text = self.uwuize(message[:1900])
        await ctx.send(
            f"**{utils.text.sanitise(ctx.author.display_name)}**\n>>> " + text,
            allowed_mentions=discord.AllowedMentions.none(),
        )

        await utils.discord.delete_message(ctx.message)

    @commands.guild_only()
    @check.acl2(check.ACLevel.MOD)
    @commands.command(name="relations-variants")
    async def relations_variants(self, ctx):
        """List relation variants on this server."""
        overwrites = RelationOverwrite.get_all(ctx.guild.id)
        if not overwrites:
            await ctx.reply(_(ctx, "This server has not enabled any variants."))
            return

        class Item:
            def __init__(self, overwrite: RelationOverwrite):
                self.relation = overwrite.command
                channel = ctx.guild.get_channel(overwrite.channel_id)
                channel_name = getattr(channel, "name", str(overwrite.channel_id))
                self.channel = f"#{channel_name}"
                self.variant = overwrite.variant

        items = [Item(overwrite) for overwrite in overwrites]

        table: List[str] = utils.text.create_table(
            items,
            header={
                "relation": _(ctx, "Relation"),
                "channel": _(ctx, "Channel"),
                "variant": _(ctx, "Variant"),
            },
        )

        for page in table:
            await ctx.send("```" + page + "```")

    @commands.guild_only()
    @check.acl2(check.ACLevel.MOD)
    @commands.command(name="relations-variant")
    async def relations_variant(
        self,
        ctx,
        command: str,
        channel: discord.TextChannel,
        variant: str = "",
    ):
        """Enable alternative relations.

        Omit the variant to show possibilities.
        """
        if command not in ACTIONS:
            await ctx.reply(_(ctx, "That relation does not exist."))
            return
        if variant == "":
            variants = ACTION_VARIANTS.get(command, [])
            current = getattr(
                RelationOverwrite.get(channel.guild.id, channel.id, command),
                "variant",
                "default",
            )
            variants = [f"**{current}**"] + [v for v in variants if v != current]
            if len(variants) == 1:
                await ctx.reply(
                    _(ctx, "Relation **{command}** does not have any variant.").format(
                        command=command
                    )
                )
                return
            await ctx.reply(
                _(ctx, "Relation **{command}** has following variants:").format(
                    command=command
                )
                + "\n>>> {variants}".format(
                    variants="\n".join(f"- {variant}" for variant in variants)
                )
            )
            return

        if variant not in ACTION_VARIANTS.get(command, []):
            await ctx.reply(_(ctx, "That relation does not have this variant."))
            return

        RelationOverwrite.set(channel.guild.id, channel.id, command, variant)
        await guild_log.info(
            ctx.author,
            ctx.channel,
            f"Relation variant for '{command}' in #{channel.name} set to '{variant}'.",
        )
        await ctx.reply(
            _(
                ctx,
                "Variant for **{command}** in **#{channel}** set to **{variant}**.",
            ).format(command=command, channel=channel.name, variant=variant)
        )

    @check.acl2(check.ACLevel.MEMBER)
    @commands.command(aliases=["rcase", "randomise"])
    async def randomcase(self, ctx, *, message: str = None):
        """raNdOMisE cAsInG"""
        if message is None:
            text = "O.o"
        else:
            text = ""
            for letter in message[:1900]:
                if letter.isalpha():
                    text += (
                        letter.upper()
                        if random.choice((True, False))
                        else letter.lower()
                    )
                else:
                    text += letter
        await ctx.send(
            f"**{utils.text.sanitise(ctx.author.display_name)}**\n>>> " + text,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await utils.discord.delete_message(ctx.message)

    async def _is_user_in_channel(self, ctx, user: discord.Member):
        if user is None or isinstance(user, discord.Role):
            return True

        if not ctx.channel.members or isinstance(ctx.channel, discord.Thread):
            members = await ctx.channel.fetch_members()
        else:
            members = ctx.channel.members

        return user.id in [m.id for m in members]

    @staticmethod
    def uwuize(string: str) -> str:
        # Adapted from https://github.com/PhasecoreX/PCXCogs/blob/master/uwu/uwu.py
        result = []

        def uwuize_word(string: str) -> str:
            with contextlib.suppress(Exception):
                if string.lower()[0] == "m" and len(string) > 2:
                    w = "W" if string[1].isupper() else "w"
                    string = string[0] + w + string[1:]
            string = string.replace("r", "w").replace("R", "W")
            string = string.replace("ř", "w").replace("Ř", "W")
            string = string.replace("l", "w").replace("L", "W")
            string = string.replace("?", "?" * random.randint(1, 3))
            string = string.replace("'", ";" * random.randint(1, 3))
            if string[-1] == ",":
                string = string[:-1] + "." * random.randint(2, 3)

            return string

        result = " ".join([uwuize_word(s) for s in string.split(" ") if len(s)])
        if result[-1] == "?":
            result += " UwU"
        if result[-1] == "!":
            result += " OwO"
        if result[-1] == ".":
            result = result[:-1] + "," * random.randint(2, 4)

        return result

    @commands.guild_only()
    @commands.cooldown(rate=2, per=10.0, type=commands.BucketType.user)
    @check.acl2(check.ACLevel.MEMBER)
    @commands.command(name="art-of-the-deal", aliases=["the-art-of-the-deal"])
    async def art_of_the_deal(self, ctx, *, member: Optional[discord.Member] = None):
        """A business man... doing business."""
        if member is None:
            member = ctx.author

        title: str = member.display_name.upper()
        title_margin_y: int = 50

        # compute font size; top bar is 1_000 x 370 px
        default_font_size: int = 10
        font_path = DATA_DIR / "the-art-of-the-deal/marlboro.regular.ttf"
        text_width, text_height = ImageFont.truetype(str(font_path)).getsize(title)
        font_scale_width: float = 1 / text_width * (1_000 - (title_margin_y * 2))
        font_scale_height: float = 1 / text_height * (370 - 160)
        font_scale = int(min(font_scale_width, font_scale_height))

        font = ImageFont.truetype(str(font_path), default_font_size * font_scale)
        true_text_width = int(font_scale * text_width)
        true_text_height = int(font_scale * text_height)

        async with ctx.typing():
            avatar: Image = await self.get_users_avatar(ctx, member)
            avatar = ImageUtils.round_image(avatar.resize((320, 320)))

            background = Image.open(DATA_DIR / "the-art-of-the-deal/background.jpg")

            frame = Image.new("RGB", (background.width, background.height), (0, 0, 0))
            frame.paste(background, (0, 0))
            frame.paste(avatar, (410, 530), avatar)

            draw = ImageDraw.Draw(frame)
            title_x = int((1_000 - true_text_width) / 2)
            title_y = int((370 - true_text_height) / 2) - title_margin_y
            draw.text((title_x, title_y), text=title, font=font, fill=(152, 110, 52))

            with BytesIO() as image_binary:
                frame.save(image_binary, format="PNG")
                image_binary.seek(0)
                await ctx.reply(
                    file=discord.File(
                        fp=image_binary, filename="the-art-of-the-deal.png"
                    ),
                    mention_author=False,
                )

    # Helper functions

    @staticmethod
    def round_image(frame_avatar: Image.Image) -> Image.Image:
        """Convert square avatar to circle"""
        frame_mask = Image.new("1", frame_avatar.size, 0)
        draw = ImageDraw.Draw(frame_mask)
        draw.ellipse((0, 0) + frame_avatar.size, fill=255)
        frame_avatar.putalpha(frame_mask)
        return frame_avatar

    @staticmethod
    async def get_users_avatar(ctx: commands.Context, user: discord.User):
        url = user.display_avatar.replace(size=256).url
        async with aiohttp.ClientSession() as session:
            response: aiohttp.ClientResponse = await session.get(url)
            if response.status != 200:
                await bot_log.warning(
                    ctx.author,
                    ctx.channel,
                    f"Could not fetch avatar for user {user}, got {response.status}.",
                )
                raise discord.HTTPException(response, "Avatar could not be fetched.")
            content: BytesIO = BytesIO(await response.read())
        avatar: Image = Image.open(content).convert("RGBA")
        return avatar

    @staticmethod
    def get_pet_frames(avatar: Image.Image) -> List[Image.Image]:
        """Get frames for the pet"""
        frames = []
        width, height = 148, 148
        vertical_offset = (0, 0, 0, 0, 1, 2, 3, 4, 5, 4, 3, 2, 2, 1, 0)

        frame_avatar = ImageUtils.round_image(avatar.resize((100, 100)))

        for i in range(14):
            img = "%02d" % (i + 1)
            frame = Image.new("RGBA", (width, height), (54, 57, 63, 1))
            frame_object = Image.open(DATA_DIR / f"pet/{img}.png")
            frame.paste(frame_avatar, (35, 25 + vertical_offset[i]), frame_avatar)
            frame.paste(frame_object, (10, 5), frame_object)
            frames.append(frame)

        return frames

    @staticmethod
    def get_hyperpet_frames(avatar: Image.Image) -> List[Image.Image]:
        """Get frames for the hyperpet"""
        frames = []
        width, height = 148, 148
        vertical_offset = (0, 1, 2, 3, 1, 0)

        avatar = ImageUtils.round_image(avatar.resize((100, 100)))
        avatar_pixels = np.array(avatar)

        for i in range(6):
            img = "%02d" % (i + 1)
            deform_hue = random.randint(0, 99) ** (i + 1) // 100**i / 100
            frame_avatar = Image.fromarray(
                ImageUtils.shift_hue(avatar_pixels, deform_hue)
            )
            frame_object = Image.open(DATA_DIR / f"hyperpet/{img}.png")

            frame = Image.new("RGBA", (width, height), (54, 57, 63, 1))
            frame.paste(frame_avatar, (35, 25 + vertical_offset[i]), frame_avatar)
            frame.paste(frame_object, (10, 5), frame_object)
            frames.append(frame)

        return frames

    @staticmethod
    def get_bonk_frames(avatar: Image.Image) -> List[Image.Image]:
        """Get frames for the bonk"""
        frames = []
        width, height = 200, 170
        deformation = (0, 0, 0, 5, 10, 20, 15, 5)

        avatar = ImageUtils.round_image(avatar.resize((100, 100)))

        for i in range(8):
            img = "%02d" % (i + 1)
            frame_avatar = avatar.resize((100, 100 - deformation[i]))
            frame_object = Image.open(DATA_DIR / f"bonk/{img}.png")

            frame = Image.new("RGBA", (width, height), (54, 57, 63, 1))
            frame.paste(frame_avatar, (80, 60 + deformation[i]), frame_avatar)
            frame.paste(frame_object, (10, 5), frame_object)
            frames.append(frame)

        return frames

    @staticmethod
    def get_whip_frames(avatar: Image.Image) -> List[Image.Image]:
        """Get frames for the whip"""
        frames = []
        width, height = 250, 150
        deformation = [0] * 8 + [2, 3, 5, 9, 6, 4, 3, 0] + [0] * 10
        translation = [0] * 9 + [1, 2, 2, 3, 3, 3, 2, 1] + [0] * 9

        avatar = ImageUtils.round_image(avatar.resize((100, 100)))

        for i in range(26):
            img = "%02d" % (i + 1)
            frame_avatar = avatar.resize((100 - deformation[i], 100))
            frame_object = Image.open(DATA_DIR / f"whip/{img}.png").resize((150, 150))

            frame = Image.new("RGBA", (width, height), (54, 57, 63, 1))
            frame.paste(
                frame_avatar, (135 + deformation[i] + translation[i], 25), frame_avatar
            )
            frame.paste(frame_object, (0, 0), frame_object)
            frames.append(frame)

        return frames

    @staticmethod
    def get_spank_frames(avatar: Image.Image) -> List[Image.Image]:
        """Get frames for the spank."""
        frames = []
        width, height = 200, 120
        deformation = (4, 2, 1, 0, 0, 0, 0, 3)

        avatar = ImageUtils.round_image(avatar.resize((100, 100)))

        for i in range(8):
            img = "%02d" % (i + 1)
            frame_avatar = avatar.resize(
                (100 + 2 * deformation[i], 100 + 2 * deformation[i])
            )
            frame_object = Image.open(DATA_DIR / f"spank/{img}.png").resize((100, 100))

            frame = Image.new("RGBA", (width, height), (54, 57, 63, 1))
            frame.paste(frame_object, (10, 15), frame_object)
            frame.paste(
                frame_avatar, (80 - deformation[i], 10 - deformation[i]), frame_avatar
            )
            frames.append(frame)

        return frames

    @staticmethod
    def get_spank_frames_figures(
        source_avatar: Image.Image, target_avatar: Image.Image
    ) -> List[Image.Image]:
        """Get frames for the spank; alternative version."""
        frames = []
        width, height = 300, 400
        target_voffset = (0, 1)
        target_hoffset = (0, 2)
        target_rotation = (310, 308)
        image_hoffset = (0, 2)

        source_avatar = ImageUtils.round_image(source_avatar.resize((84, 84)))
        target_avatar = ImageUtils.round_image(target_avatar.resize((100, 100)))

        for i in range(2):
            img = ("01", "02")[i]
            rotated_avatar = target_avatar.rotate(target_rotation[i])
            frame_object = Image.open(DATA_DIR / f"spank_figures/{img}.png")
            frame_source_avatar = source_avatar.resize((64, 64))
            frame_target_avatar = rotated_avatar.resize((64, 64))
            frame = Image.new("RGBA", (width, height), (54, 57, 63, 1))

            frame.paste(
                frame_target_avatar,
                (220 + target_voffset[i], 140 + target_hoffset[i]),
                frame_target_avatar,
            )
            frame.paste(
                frame_object,
                (0, 65 + image_hoffset[i]),
                frame_object,
            )
            frame.paste(
                frame_source_avatar,
                (115, 20 + image_hoffset[i]),
                frame_source_avatar,
            )
            frames.append(frame)

        return frames

    @staticmethod
    def get_lick_frames(avatar: Image.Image) -> List[Image.Image]:
        """Get frames for the lick"""
        frames = []
        width, height = 270, 136
        voffset = (0, 2, 1, 2)
        hoffset = (-2, 0, 2, 0)

        avatar = ImageUtils.round_image(avatar.resize((100, 100)))

        for i in range(4):
            img = ("01", "02", "03", "02")[i]
            frame_avatar = avatar.resize((64, 64))
            frame_object = Image.open(DATA_DIR / f"lick/{img}.png")

            frame = Image.new("RGBA", (width, height), (54, 57, 63, 1))
            frame.paste(frame_object, (10, 15), frame_object)
            frame.paste(frame_avatar, (198 + voffset[i], 68 + hoffset[i]), frame_avatar)
            frames.append(frame)

        return frames

    @staticmethod
    def get_hyperlick_frames(avatar: Image.Image) -> List[Image.Image]:
        """Get frames for the hyperlick"""
        frames = []
        width, height = 270, 136
        voffset = (0, 3, -1, 3)
        hoffset = (-2, 0, 2, 0)

        avatar = ImageUtils.round_image(avatar.resize((64, 64)))
        avatar_pixels = np.array(avatar)

        for i in range(4):
            img = ("01", "02", "03", "02")[i]
            deform_hue = random.randint(0, 99) ** (i + 1) // 100**i / 100
            frame_avatar = Image.fromarray(
                ImageUtils.shift_hue(avatar_pixels, deform_hue)
            )
            frame_object = Image.open(DATA_DIR / f"lick/{img}.png")

            frame = Image.new("RGBA", (width, height), (54, 57, 63, 1))
            frame.paste(frame_object, (10, 15), frame_object)
            frame.paste(frame_avatar, (198 + voffset[i], 68 + hoffset[i]), frame_avatar)
            frames.append(frame)

        return frames

    @staticmethod
    def get_action_embed(
        ctx: commands.Context, user: Union[discord.User, discord.Member], action: str
    ) -> Optional[discord.Embed]:
        gave, got = Relation.get_user_relation(ctx.guild.id, user.id, action)
        if not gave and not got:
            return None

        embed = utils.discord.create_embed(
            title=_(ctx, "Relations {name}: {action}").format(
                name=utils.text.sanitise(user.display_name), action=action
            ),
            description=_(
                ctx, "Relation statistics: {gave} given, {got} received."
            ).format(gave=gave, got=got),
            author=ctx.author,
        )

        given = Relation.get_given_top(
            ctx.guild.id, user.id, action, limit=EMBED_LIST_LIMIT
        )
        if given:
            content: List[str] = []
            for item in given:
                member = ctx.guild.get_member(item.receiver_id)
                member_str = (
                    utils.text.sanitise(member.display_name)
                    if member
                    else "*" + _(ctx, "Unknown user") + "*"
                )
                content.append(f"`{item.value:>3}` … {member_str}")

            embed.add_field(
                name=_(ctx, "Given"),
                value="\n".join(content),
                inline=False,
            )
        else:
            embed.add_field(
                name=_(ctx, "Nothing given"),
                value=_(ctx, "No data available."),
                inline=False,
            )

        received = Relation.get_received_top(
            ctx.guild.id, user.id, action, limit=EMBED_LIST_LIMIT
        )
        if received:
            content: List[str] = []
            for item in received:
                member = ctx.guild.get_member(item.sender_id)
                member_str = (
                    utils.text.sanitise(member.display_name)
                    if member
                    else "*" + _(ctx, "Unknown user") + "*"
                )
                content.append(f"`{item.value:>3}` … {member_str}")

            embed.add_field(
                name=_(ctx, "Received"),
                value="\n".join(content),
                inline=False,
            )
        else:
            embed.add_field(
                name=_(ctx, "Nothing received"),
                value=_(ctx, "No data available."),
                inline=False,
            )

        return embed


async def setup(bot) -> None:
    await bot.add_cog(Fun(bot))
