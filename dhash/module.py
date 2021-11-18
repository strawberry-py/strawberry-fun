import asyncio
import dhash
import time
from io import BytesIO
from PIL import Image
import nextcord
from nextcord.ext import commands

from core import utils, i18n, logger, check, TranslationContext
from .database import HashChannel, ImageHash

_ = i18n.Translator("modules/fun").translate
guild_log = logger.Guild.logger()
bot_log = logger.Bot.logger()

LIMIT_FULL = 3
LIMIT_HARD = 7
LIMIT_SOFT = 14

MAX_ATTACHMENT_SIZE = 8000


class Dhash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.embed_cache = {}

    def _in_repost_channel(self, message: nextcord.Message) -> bool:
        if message.guild is None:
            return False
        if message.attachments is None or not len(message.attachments):
            return False
        if message.author.bot:
            return False

        channel = HashChannel.get(message.guild.id, message.channel.id)
        if not channel:
            return False

        return True

    @commands.guild_only()
    @commands.check(check.acl)
    @commands.group(name="dhash")
    async def dhash(self, ctx):
        await utils.Discord.send_help(ctx)

    @commands.check(check.acl)
    @dhash.command(name="add")
    async def dhash_add(
        self, ctx, channel: nextcord.TextChannel, reaction_limit: int = 5
    ):
        hash_channel = HashChannel.get(ctx.guild.id, channel.id)
        if hash_channel:
            await ctx.send(
                _(
                    ctx,
                    "{channel} is already hash channel.",
                ).format(channel=channel.mention)
            )
            return

        hash_channel = HashChannel.add(ctx.guild.id, channel.id, reaction_limit)
        await ctx.send(
            _(
                ctx,
                "Channel {channel} added as hash channel with reaction limit **{reaction_limit}**.",
            ).format(channel=channel.mention, reaction_limit=reaction_limit)
        )
        await guild_log.info(
            ctx.author,
            ctx.channel,
            f"Channel #{channel.name} set as hash channel with reaction limit {reaction_limit}.",
        )

    @commands.check(check.acl)
    @dhash.command(name="limit")
    async def dhash_limit(
        self, ctx, channel: nextcord.TextChannel, reaction_limit: int
    ):
        hash_channel = HashChannel.get(ctx.guild.id, channel.id)

        if not hash_channel:
            await ctx.send(
                _(
                    ctx,
                    "{channel} is not hash channel.",
                ).format(channel=channel.mention)
            )
            return

        if reaction_limit < 1:
            await ctx.send(
                _(
                    ctx,
                    "Reaction limit must be higher than 0.",
                ).format(channel=channel.mention)
            )
            return

        hash_channel.set_limit(reaction_limit)
        await ctx.send(
            _(
                ctx,
                "Changed reaction limit for {channel} to **{reaction_limit}**.",
            ).format(channel=channel.mention, reaction_limit=reaction_limit)
        )
        await guild_log.info(
            ctx.author,
            ctx.channel,
            f"Changed reaction limit for channel #{channel.name} to {reaction_limit}.",
        )

    @commands.check(check.acl)
    @dhash.command(name="list")
    async def dhash_list(self, ctx):
        hash_channels = HashChannel.get_all(ctx.guild.id)
        if not hash_channels:
            await ctx.reply(_(ctx, "This server has no hash channels."))
            return

        channels = [ctx.guild.get_channel(c.channel_id) for c in hash_channels]
        column_name_width: int = max([len(c.name) for c in channels if c])

        result = []
        for hash_channel, channel in zip(hash_channels, channels):
            name = getattr(channel, "name", "???")
            line = f"#{name:<{column_name_width}} {hash_channel.channel_id} {hash_channel.reaction_limit}"
            result.append(line)

        await ctx.reply("```" + "\n".join(result) + "```")

    @commands.check(check.acl)
    @dhash.command(name="remove", aliases=["rem"])
    async def dhash_remove(self, ctx, channel: nextcord.TextChannel):
        if HashChannel.remove(ctx.guild.id, channel.id):
            message = _(ctx, "Hash channel {channel} removed.")
            await guild_log.info(
                ctx.author,
                ctx.channel,
                f"Channel #{channel.name} is no longer a hash channel.",
            )
        else:
            message = _(ctx, "{channel} is not hash channel.")
        await ctx.reply(message.format(channel=channel.mention))

    @commands.check(check.acl)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.bot_has_permissions(read_message_history=True)
    @dhash.command(name="history")
    async def dhash_history(self, ctx, limit: int):
        """Scan current channel for images and save them as hashes.
        limit: How many messages should be scanned. Negative to scan all.
        """
        if limit < 0:
            limit = None

        async with ctx.typing():
            messages = await ctx.channel.history(limit=limit).flatten()

        status = await ctx.send(
            _(ctx, "**LOADING**")
            + "\n"
            + _(ctx, "Downloaded **{count}** messages.").format(count=len(messages))
        )

        await asyncio.sleep(1)

        ctr_nofile: int = 0
        ctr_hashes: int = 0
        now = time.time()
        for i, message in enumerate(messages, 1):
            if i % 50 == 0:
                await status.edit(
                    content=(
                        _(ctx, "**SCANNING**")
                        + "\n"
                        + _(
                            ctx,
                            "Processed **{count}** out of **{total}** messages ({percent} %).",
                        )
                        + "\n"
                        + _(ctx, "Calculated **{hashes}** hashes.")
                    ).format(
                        count=i,
                        total=len(messages),
                        percent="{:.1f}".format(i / len(messages) * 100),
                        hashes=ctr_hashes,
                    )
                )

            if not len(message.attachments):
                ctr_nofile += 1
                continue

            hashes = [x async for x in self._save_hashes(message)]
            ctr_hashes += len(hashes)

        await status.edit(
            content=(
                _(ctx, "**COMPLETED**")
                + "\n"
                + _(ctx, "Processed **{messages}** messages.")
                + "\n"
                + _(
                    ctx,
                    "Calculated **{hashes}** image hashes in **{seconds}** seconds.",
                )
            ).format(
                messages=len(messages),
                hashes=ctr_hashes,
                seconds="{:.1f}".format(time.time() - now),
            )
        )

    @commands.check(check.acl)
    @dhash.command(name="compare", aliases=["messages"])
    async def dhash_compare(self, ctx, messages: commands.Greedy[nextcord.Message]):
        """Display hashes of given messages.
        messages: Space separated list of messages.
        """
        text = []

        for message in messages:
            db_images = ImageHash.get_by_message(message.guild.id, message.id)
            if not len(db_images):
                continue

            text.append(
                _(ctx, "Message **`{message_id}`**").format(message_id=message.id)
            )
            for db_image in db_images:
                text.append("   > `{hash}`".format(hash=db_image.dhash[2:]))
            text.append("")

        if not len(text):
            return await ctx.send(_(ctx, "Messages has no associtated hashes."))

        await ctx.send("\n".join(text))

    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        if self._in_repost_channel(message):
            await self._check_message(message)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: nextcord.RawMessageDeleteEvent):
        channel = HashChannel.get(payload.guild_id, payload.channel_id)
        if channel:
            ImageHash.delete_by_message(payload.guild_id, payload.message_id)

    @commands.Cog.listener()
    async def on_message_delete(self, message: nextcord.Message):
        if not self._in_repost_channel(message):
            return

        # delete repost embed if we have the report message cached

        if message.author == self.bot.user:
            return

        if message.id in self.embed_cache:
            try:
                report = self.embed_cache[message.id]
                await report.delete()
            except nextcord.errors.HTTPException as exc:
                await bot_log.error(
                    message.author,
                    message,
                    f"Could not delete repost embed {message.id} at guild {message.guild.id} using cache.",
                    exception=exc,
                )
            self.embed_cache.pop(message.id)
            return

        # try to find and delete repost report embed, because we don't have it cached
        messages = await message.channel.history(
            after=message, limit=3, oldest_first=True
        ).flatten()
        for report in messages:
            if not report.author.bot:
                continue
            if len(report.embeds) != 1 or type(report.embeds[0].footer.text) != str:
                continue
            if str(message.id) != report.embeds[0].footer.text.split(" | ")[1]:
                continue

            try:
                await report.delete()
            except nextcord.errors.HTTPException as exc:
                await bot_log.error(
                    message.author,
                    message,
                    "Could not delete repost embed {msg_id} at guild {guild}".format(
                        msg_id=message.id, guild=message.guild.id
                    ),
                    exception=exc,
                )
            break

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle 'This is a repost' report.
        The footer contains reposter's user ID and repost message id.
        """
        hash_channel = HashChannel.get(payload.guild_id, payload.channel_id)

        if not hash_channel:
            return
        if payload.member.bot:
            return

        emoji = str(payload.emoji)

        if emoji != "❎":
            return

        channel = self.bot.get_guild(payload.guild_id).get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        if not message.author.bot:
            return

        for report_reaction in message.reactions:
            if str(report_reaction) != "❎":
                continue

            if report_reaction.count > hash_channel.reaction_limit:
                # remove bot's reaction, it is not a repost

                try:
                    repost_message_id = int(
                        message.embeds[0].footer.text.split(" | ")[1]
                    )

                    if repost_message_id in self.embed_cache:
                        self.embed_cache.pop(repost_message_id)

                    repost_message = await message.channel.fetch_message(
                        repost_message_id
                    )

                    await repost_message.remove_reaction("\u267B", self.bot.user)
                except nextcord.errors.HTTPException as exc:
                    return await bot_log.error(
                        message.author,
                        message,
                        "Could not delete bot reactions from message {msg_id} at guild {guild}".format(
                            msg_id=message.id, guild=message.guild.id
                        ),
                        exception=exc,
                    )
                return await utils.Discord.delete_message(message)

    # Helper functions

    async def _save_hashes(self, message: nextcord.Message):
        for attachment in message.attachments:
            if attachment.size > MAX_ATTACHMENT_SIZE * 1024:
                continue

            extension = attachment.filename.split(".")[-1].lower()
            if extension not in ("jpg", "jpeg", "png", "webp", "gif"):
                continue

            fp = BytesIO()

            await attachment.save(fp)
            try:
                image = Image.open(fp)
            except OSError:
                continue

            h = dhash.dhash_int(image)
            ImageHash.add(
                guild_id=message.guild.id,
                channel_id=message.channel.id,
                message_id=message.id,
                attachment_id=attachment.id,
                hash=str(hex(h)),
            )
            yield h

    async def _check_message(self, message: nextcord.Message):
        """Check if message contains duplicate image."""
        image_hashes = [x async for x in self._save_hashes(message)]

        duplicates = {}
        all_images = None

        for image_hash in image_hashes:
            # try to look up hash directly
            images = ImageHash.get_hash(
                message.guild.id, message.channel.id, str(hex(image_hash))
            )
            duplicated = False

            for image in images:
                # skip current message
                if image.message_id == message.id:
                    continue
                # add to duplicates
                duplicates[image] = 0
                duplicated = True
                break

            # move on to the next hash
            if duplicated:
                continue

            # full match not found, iterate over whole database
            if all_images is None:
                all_images = ImageHash.get_by_channel(
                    message.guild.id, message.channel.id
                )

            minimal_distance = 128
            duplicate = None
            for image in all_images:
                # skip current image
                if image.message_id == message.id:
                    continue

                # do the comparison
                db_image_hash = int(image.hash, 16)
                distance = dhash.get_num_bits_different(db_image_hash, image_hash)
                if distance < minimal_distance:
                    duplicate = image
                    minimal_distance = distance

            if minimal_distance < LIMIT_SOFT:
                duplicates[duplicate] = minimal_distance

        for image_hash, distance in duplicates.items():
            await self._report_duplicate(message, image_hash, distance)

    async def _report_duplicate(
        self, message: nextcord.Message, original: ImageHash, distance: int
    ):
        """Send report.
        message: The new message containing attachment repost.
        original: The original attachment.
        distance: Hamming distance between the original and repost.
        """
        utx = TranslationContext(message.guild.id, message.author.id)

        if distance <= LIMIT_FULL:
            level = _(utx, "**♻ This is repost!**")
        elif distance <= LIMIT_HARD:
            level = _(utx, "**♻ This is probably repost!**")
        else:
            level = _(utx, "🤷🏻 This could be repost.")

        await message.add_reaction("♻")

        similarity = "{:.1f} %".format((1 - distance / 128) * 100)
        timestamp = utils.Time.id_to_datetime(original.attachment_id).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        try:
            original_channel = message.guild.get_channel(original.channel_id)
            original_message = await original_channel.fetch_message(original.message_id)
            author = nextcord.utils.escape_markdown(
                original_message.author.display_name
            )
            link = f"[**{author}**, {timestamp}]({original_message.jump_url})"
        except nextcord.errors.NotFound:
            link = "404 😿"

        description = _(utx, "{name}, matching **{similarity}**!").format(
            name=nextcord.utils.escape_markdown(message.author.display_name),
            similarity=similarity,
        )

        embed = utils.Discord.create_embed(
            title=level, description=description, color=nextcord.Colour.orange()
        )

        embed.add_field(
            name=_(utx, "Original"),
            value=link,
            inline=False,
        )

        embed.add_field(
            name=_(utx, "Hint"),
            value=_(
                utx,
                "_If image is repost, give it ♻️ reaction. "
                "If it's not, click here on ❎ and when we reach {limit} reactions, "
                "this message will be deleted._",
            ).format(
                limit=HashChannel.get(
                    message.guild.id, message.channel.id
                ).reaction_limit,
            ),
            inline=False,
        )
        embed.set_footer(text=f"{message.author.id} | {message.id}")

        report = await message.reply(embed=embed)

        self.embed_cache[message.id] = report

        await report.add_reaction("❎")


def setup(bot) -> None:
    bot.add_cog(Dhash(bot))
