import aiohttp
import contextlib
import random
import numpy as np
from io import BytesIO
from PIL import Image, ImageDraw
from typing import List, Union
from pathlib import Path

import nextcord
from nextcord.ext import commands

import database.config
from core import utils, i18n

from .database import Relation
from .image_utils import ImageUtils

_ = i18n.Translator("modules/fun").translate
config = database.config.Config.get()

DATA_DIR = Path(__file__).parent / "data"


class Meme(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @commands.cooldown(rate=5, per=20.0, type=commands.BucketType.user)
    @commands.command()
    async def hug(self, ctx, *, user: Union[nextcord.Member, nextcord.Role] = None):
        """Hug someone"""
        if user is None:
            source = self.bot.user
            target = ctx.author
        else:
            source = ctx.author
            target = user

        if type(target) == nextcord.Role:
            Relation.add(ctx.guild.id, source.id, None, "hug")
        else:
            Relation.add(ctx.guild.id, source.id, target.id, "hug")

        border: str = "***" if type(target) == nextcord.Role else "**"
        hug_emoji: str = "(⊃・‿・)⊃" if random.randint(1, 20) < 20 else "⊃・﹏・)⊃"
        await ctx.send(f"{hug_emoji} {border}{target.name}{border}")

    @commands.guild_only()
    @commands.cooldown(rate=5, per=20.0, type=commands.BucketType.user)
    @commands.command()
    async def whip(self, ctx, *, user: nextcord.Member = None):
        """Whip someone"""
        if user is None:
            source = self.bot.user
            target = ctx.author
        else:
            source = ctx.author
            target = user

        Relation.add(ctx.guild.id, source.id, target.id, "whip")

        async with ctx.typing():
            url = target.display_avatar.replace(size=256).url
            async with aiohttp.ClientSession() as session:
                response: aiohttp.ClientResponse = await session.get(url)
                content: BytesIO = BytesIO(await response.read())
                avatar: Image = Image.open(content).convert("RGBA")

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
                        file=nextcord.File(fp=image_binary, filename="whip.gif"),
                        mention_author=False,
                    )

    @commands.guild_only()
    @commands.cooldown(rate=5, per=20.0, type=commands.BucketType.user)
    @commands.command()
    async def spank(self, ctx, *, user: nextcord.Member = None):
        """Spank someone"""
        if user is None:
            source = self.bot.user
            target = ctx.author
        else:
            source = ctx.author
            target = user

        Relation.add(ctx.guild.id, source.id, target.id, "spank")

        async with ctx.typing():
            url = target.display_avatar.replace(size=256).url
            async with aiohttp.ClientSession() as session:
                response: aiohttp.ClientResponse = await session.get(url)
                content: BytesIO = BytesIO(await response.read())
                avatar: Image = Image.open(content).convert("RGBA")

                frames = self.get_spank_frames(avatar)

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
                        file=nextcord.File(fp=image_binary, filename="spank.gif"),
                        mention_author=False,
                    )

    @commands.guild_only()
    @commands.cooldown(rate=5, per=20.0, type=commands.BucketType.user)
    @commands.command()
    async def pet(self, ctx, *, user: nextcord.Member = None):
        """Pet someone"""
        if user is None:
            source = self.bot.user
            target = ctx.author
        else:
            source = ctx.author
            target = user

        Relation.add(ctx.guild.id, source.id, target.id, "pet")

        async with ctx.typing():
            url = target.display_avatar.replace(size=256).url
            async with aiohttp.ClientSession() as session:
                response: aiohttp.ClientResponse = await session.get(url)
                content: BytesIO = BytesIO(await response.read())
                avatar: Image = Image.open(content).convert("RGBA")

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
                        file=nextcord.File(fp=image_binary, filename="pet.gif"),
                        mention_author=False,
                    )

    @commands.guild_only()
    @commands.cooldown(rate=5, per=20.0, type=commands.BucketType.user)
    @commands.command()
    async def hyperpet(self, ctx, *, user: nextcord.Member = None):
        """Hyperpet someone"""
        if user is None:
            source = self.bot.user
            target = ctx.author
        else:
            source = ctx.author
            target = user

        Relation.add(ctx.guild.id, source.id, target.id, "hyperpet")

        async with ctx.typing():
            url = target.display_avatar.replace(size=256).url
            async with aiohttp.ClientSession() as session:
                response: aiohttp.ClientResponse = await session.get(url)
                content: BytesIO = BytesIO(await response.read())
                avatar: Image = Image.open(content).convert("RGBA")

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
                        file=nextcord.File(fp=image_binary, filename="hyperpet.gif"),
                        mention_author=False,
                    )

    @commands.guild_only()
    @commands.cooldown(rate=5, per=20.0, type=commands.BucketType.user)
    @commands.command()
    async def bonk(self, ctx, *, user: nextcord.Member = None):
        """Bonk someone

        member: Discord user. If none, the bot will bonk you.
        """
        if user is None:
            source = self.bot.user
            target = ctx.author
        else:
            source = ctx.author
            target = user

        Relation.add(ctx.guild.id, source.id, target.id, "bonk")

        async with ctx.typing():
            url = target.display_avatar.replace(size=256).url
            async with aiohttp.ClientSession() as session:
                response: aiohttp.ClientResponse = await session.get(url)
                content: BytesIO = BytesIO(await response.read())
                avatar: Image = Image.open(content).convert("RGBA")

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
                        file=nextcord.File(fp=image_binary, filename="bonk.gif"),
                        mention_author=False,
                    )

    @commands.guild_only()
    @commands.cooldown(rate=5, per=20.0, type=commands.BucketType.user)
    @commands.command()
    async def slap(self, ctx, *, user: Union[nextcord.Member, nextcord.Role] = None):
        """Slap someone"""
        if user is None:
            source = self.bot.user
            target = ctx.author
        else:
            source = ctx.author
            target = user

        options = ["つ", "づ", "ノ"]

        target_name: str
        border: str
        if type(target) == nextcord.Role:
            Relation.add(ctx.guild.id, source.id, None, "slap")
            target_name = target.name
            border = "***"
        else:
            Relation.add(ctx.guild.id, source.id, target.id, "slap")
            target_name = target.display_name
            border = "**"

        await ctx.reply(
            "{source} {slap} {border}{target}{border}".format(
                source=utils.Text.sanitise(source.display_name),
                slap=random.choice(options),
                border=border,
                target=utils.Text.sanitise(target_name),
            ),
            mention_author=False,
        )

    @commands.guild_only()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command()
    async def relations(self, ctx, *, user: nextcord.User = None):
        """Get your information about hugs, pets, ..."""
        await utils.Discord.delete_message(ctx.message)

        if user is None:
            user = ctx.author

        embed = utils.Discord.create_embed(
            author=ctx.author,
            title=_(ctx, "Relations"),
            description=_(ctx, "gave / got"),
        )

        avatar_url: str = user.display_avatar.replace(size=256).url
        embed.set_thumbnail(url=avatar_url)

        for action in ("hug", "pet", "hyperpet", "slap", "bonk", "spank", "whip"):
            action_stats = Relation.get_user_relation(ctx.guild.id, user.id, action)

            if action_stats[0] == 0 and action_stats[1] == 0:
                continue

            embed.add_field(
                name=action,
                value=f"{action_stats[0]} / {action_stats[1]}",
            )

        await ctx.send(embed=embed)

    @commands.command(aliases=["owo"])
    async def uwu(self, ctx, *, message: str = None):
        """UWUize message"""
        if message is None:
            text = "OwO!"
        else:
            text = utils.Text.sanitise(self.uwuize(message), limit=1900, escape=False)
        await ctx.send(
            f"**{utils.Text.sanitise(ctx.author.display_name)}**\n>>> " + text
        )

        await utils.Discord.delete_message(ctx.message)

    @commands.command(aliases=["rcase", "randomise"])
    async def randomcase(self, ctx, *, message: str = None):
        """raNdOMisE cAsInG"""
        if message is None:
            text = "O.o"
        else:
            text = ""
            for letter in message:
                if letter.isalpha():
                    text += (
                        letter.upper()
                        if random.choice((True, False))
                        else letter.lower()
                    )
                else:
                    text += letter
                text = utils.Text.sanitise(text, limit=1960)
        await ctx.send(
            f"**{utils.Text.sanitise(ctx.author.display_name)}**\n>>> " + text
        )
        await utils.Discord.delete_message(ctx.message)

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

    @staticmethod
    def round_image(frame_avatar: Image.Image) -> Image.Image:
        """Convert square avatar to circle"""
        frame_mask = Image.new("1", frame_avatar.size, 0)
        draw = ImageDraw.Draw(frame_mask)
        draw.ellipse((0, 0) + frame_avatar.size, fill=255)
        frame_avatar.putalpha(frame_mask)
        return frame_avatar

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
            deform_hue = random.randint(0, 99) ** (i + 1) // 100 ** i / 100
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
        """Get frames for the spank"""
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


def setup(bot) -> None:
    bot.add_cog(Meme(bot))
