import aiohttp
import datetime
import json
from typing import Optional, List

import nextcord
from nextcord.ext import commands

import pie.database.config
from pie import check, i18n, logger, utils

from .database import Place

translator = i18n.Translator("modules/fun")
_ = translator.translate
guild_log = logger.Guild.logger()
config = pie.database.config.Config.get()
bot_log = logger.Bot.logger()

# number of days to get forecast for (including current day, max is 3)
NUM_OF_FORECAST_DAYS = 3
# dict for getting the data from json easier (when you don't wan't some phase of day comment it)
DAY_PHASES = {
    "Morning": 2,
    "Day": 4,
    "Evening": 6,
    "Night": 7,
}


class Weather(commands.Cog):
    """Weather and forecast"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _translate_day_phase(self, ctx: commands.Context, day_phase: str) -> str:
        if day_phase == "Morning":
            return _(ctx, "Morning")
        if day_phase == "Day":
            return _(ctx, "Day")
        if day_phase == "Evening":
            return _(ctx, "Evening")
        if day_phase == "Night":
            return _(ctx, "Night")

    def _get_current_day_phase(self, ctx: commands.Context) -> str:
        now = datetime.datetime.now()
        if now.hour <= 6:
            return _(ctx, "Morning")
        if now.hour <= 12:
            return _(ctx, "Day")
        if now.hour <= 18:
            return _(ctx, "Evening")
        return _(ctx, "Night")

    def _get_useful_data(
        self, all_data: dict, ctx: commands.Context, lang_preference: str
    ) -> List[dict]:
        """
        example json: https://wttr.in/praha?lang=sk&format=j1
        get useful data from json as list of individual days
        """

        # get individual days to extract data
        weather = []
        nearest_place = all_data["nearest_area"][0]["areaName"][0]["value"]
        lang_preference = f"lang_{lang_preference}"
        for i in range(NUM_OF_FORECAST_DAYS):
            day = all_data["weather"][i]
            day_dict = {
                "date": day["date"],
                "nearest_place": nearest_place,
            }
            day = day["hourly"]
            for day_phase, hour in DAY_PHASES.items():
                if lang_preference != "lang_en":
                    lang_or_desc = lang_preference
                else:
                    lang_or_desc = "weatherDesc"
                day_dict.update(
                    {
                        self._translate_day_phase(ctx, day_phase): {
                            "state": day[hour][lang_or_desc][0]["value"],
                            "temp": day[hour]["tempC"],
                            "feels_like": day[hour]["FeelsLikeC"],
                            "wind_speed": day[hour]["windspeedKmph"],
                            "rain_chance": day[hour]["chanceofrain"],
                        }
                    }
                )

            weather.append(day_dict)
        return weather

    async def _create_embeds(
        self, ctx: commands.Context, name: str, lang_preference: str
    ) -> List[nextcord.Embed]:
        """create embeds for scrollable embed"""
        url = f"https://wttr.in/{name}?format=j1&lang={lang_preference}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.text()
        except aiohttp.ClientResponseError as e:
            await guild_log.warning(
                ctx.author,
                ctx.channel,
                f'An error occured while getting weather info, err code "{e.code}"',
            )
            return [
                utils.discord.create_embed(
                    author=ctx.message.author,
                    title=_(ctx, "An error occured while getting weather info."),
                    error=True,
                )
            ]

        try:
            resp_json = json.loads(data)
        except json.JSONDecodeError:
            await bot_log.error(
                ctx.author,
                ctx.channel,
                f"Did not receive JSON response: {resp!s} {data!s}.",
            )
            return [
                utils.discord.create_embed(
                    author=ctx.message.author,
                    title=_(ctx, "Did not receive JSON response."),
                    error=True,
                )
            ]

        current_day_phase: str = self._get_current_day_phase(ctx)

        # create day embeds
        days = self._get_useful_data(resp_json, ctx, lang_preference)
        embeds = []
        for i, day in enumerate(days):
            title: str
            if i == 0:
                title = _(ctx, "Today")
            elif i == 1:
                title = _(ctx, "Tomorrow")
            else:
                title = _(ctx, day["date"])

            if i == 0:
                # Show current weather in title
                now = day[current_day_phase]
                title = f"{title}: {now['state']}, {now['temp']} ˚C"
            else:
                # Show maximum and minimum in title
                temperatures = [
                    int(info["temp"])
                    for phase, info in day.items()
                    if type(info) is dict
                ]
                min_t, max_t = min(temperatures), max(temperatures)
                title = f"{title}: {min_t}\N{EN DASH}{max_t} °C"

            embed = utils.discord.create_embed(
                author=ctx.message.author,
                title=title,
                description=_(ctx, "Weather forecast for **{place}**, {date}").format(
                    date=day["date"], place=name
                ),
            )

            skip_day_phase: bool = True
            for day_phase, weather_info in day.items():
                # skip 'date' and 'nearest_place' strings
                if type(weather_info) != dict:
                    continue
                # skip today's day phase if it has already ended
                if day_phase == current_day_phase:
                    skip_day_phase = False
                if i == 0 and skip_day_phase:
                    continue

                embed.add_field(
                    name=f"{day_phase}: {weather_info['state']}",
                    value=_(
                        ctx, "Temperature: **{real} ˚C** (feels like **{feel} ˚C**)"
                    ).format(
                        real=weather_info["temp"],
                        feel=weather_info["feels_like"],
                    )
                    + "\n"
                    + _(ctx, "Wind speed: **{wind} km/h**").format(
                        wind=weather_info["wind_speed"],
                    )
                    + "\n"
                    + _(ctx, "Chance of rain: **{rain} %**").format(
                        rain=weather_info["rain_chance"],
                    ),
                    inline=False,
                )

            embeds.append(embed)

        # create the last "map" embed
        embed = utils.discord.create_embed(
            author=ctx.message.author,
            title=_(ctx, "Weather map for today"),
            description=name,
        )
        img_url = f"https://v3.wttr.in/{name}.png"
        embed.set_image(url=img_url)
        embeds.append(embed)
        return embeds

    @commands.guild_only()
    @check.acl2(check.ACLevel.MEMBER)
    @commands.command(name="set-weather-place")
    async def set_weather_place(self, ctx, *, name: str):
        """Set preferred place for weather and forecast information."""
        if not self._place_is_valid(name):
            await ctx.reply(_(ctx, "That's not valid place name."))
            return
        Place.set(ctx.guild.id, ctx.author.id, name)
        await guild_log.debug(
            ctx.author, ctx.channel, f"Preferred weather place set to {name}."
        )
        await ctx.reply(
            _(ctx, "Your preferred weather place set to **{place}**.").format(
                place=name
            )
        )

    @commands.guild_only()
    @check.acl2(check.ACLevel.MEMBER)
    @commands.command(name="unset-weather-place")
    async def unset_weather_place(self, ctx):
        """Unset preferred place for weather and forecast information."""
        if Place.remove(ctx.guild.id, ctx.author.id) == 0:
            await ctx.reply(_(ctx, "You don't have any place preference saved."))
            return
        await guild_log.debug(ctx.author, ctx.channel, "Preferred weather place unset.")
        await ctx.reply(_(ctx, "Your preferred weather place was removed."))

    @commands.guild_only()
    @check.acl2(check.ACLevel.MOD)
    @commands.command(name="set-guild-weather-place")
    async def set_guild_weather_place(self, ctx, *, name: str):
        """Set guild's preferred place for weather and forecast information."""
        if not self._place_is_valid(name):
            await ctx.reply(_(ctx, "That's not valid place name."))
            return
        Place.set(ctx.guild.id, None, name)
        await guild_log.info(
            ctx.author, ctx.channel, f"Guild's preferred weather place set to {name}."
        )
        await ctx.reply(
            _(ctx, "Server's preferred weather place set to **{place}**.").format(
                place=name
            )
        )

    @commands.guild_only()
    @check.acl2(check.ACLevel.MOD)
    @commands.command(name="unset-guild-weather-place")
    async def unset_guild_weather_place(self, ctx):
        """Unset guild's preferred place for weather and forecast information."""
        if Place.remove(ctx.guild.id, None) == 0:
            await ctx.reply(
                _(ctx, "This server doesn't have any place preference saved.")
            )
            return
        await guild_log.debug(
            ctx.author, ctx.channel, "Guild's preferred weather place unset."
        )
        await ctx.reply(_(ctx, "Server's preferred weather place was removed."))

    @commands.guild_only()
    @check.acl2(check.ACLevel.MEMBER)
    @commands.command(
        name="weather-place",
        aliases=["weather-places", "weather-preference"],
    )
    async def weather_places(self, ctx):
        """Diplay your and server preference for forecast."""
        user_place = Place.get(ctx.guild.id, ctx.author.id)
        guild_place = Place.get(ctx.guild.id, None)

        embed = utils.discord.create_embed(
            title=_(ctx, "Weather forecast preference"),
            author=ctx.author,
        )
        embed.add_field(
            name=_(ctx, "Your preference"),
            value=getattr(user_place, "name", _(ctx, "*No preference set*")),
            inline=False,
        )
        embed.add_field(
            name=_(ctx, "Server preference"),
            value=getattr(guild_place, "name", _(ctx, "*No preference set*")),
            inline=False,
        )
        await ctx.reply(embed=embed)

    @commands.guild_only()
    @check.acl2(check.ACLevel.MEMBER)
    @commands.command(name="weather")
    async def weather(self, ctx, *, name: Optional[str] = None):
        """Get weather information on any place."""
        if name is None:
            # try to get user preference
            place = Place.get(ctx.guild.id, ctx.author.id)
            if place is not None:
                name = place.name
        if name is None:
            # try to get guild preference
            place = Place.get(ctx.guild.id, None)
            if place is not None:
                name = place.name
        if name is None:
            await ctx.reply(_(ctx, "You have to specify a place or set a preference."))
            return

        lang_preference = translator.get_language_preference(ctx)
        async with ctx.typing():
            embeds = await self._create_embeds(ctx, name, lang_preference)
            scroll_embed = utils.ScrollableEmbed(ctx, embeds)
        await scroll_embed.scroll()

    def _place_is_valid(self, name: str) -> bool:
        if "&" in name:
            return False
        return True


def setup(bot) -> None:
    bot.add_cog(Weather(bot))
