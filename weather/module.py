from typing import Optional, List
import aiohttp

import nextcord
from nextcord.ext import commands

import pie.database.config
from pie import check, i18n, logger, utils

from .database import Place

translator = i18n.Translator("modules/fun")
_ = translator.translate
guild_log = logger.Guild.logger()
config = pie.database.config.Config.get()

# number of days to get forecast for (including current day, max is 3)
NUM_OF_FORECAST_DAYS = 3
# dict for getting the data from json easier (when you don't wan't some phase of day comment it)
DAY_PHASES = {
    "Morning": 2,
    "Day": 4,
    # "Evening": 6,
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
                    resp_json = await resp.json()
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

        # create day embeds
        days = self._get_useful_data(resp_json, ctx, lang_preference)
        embeds = []
        for day in days:
            embed = utils.discord.create_embed(
                author=ctx.message.author,
                title=_(ctx, "Weather forecast for _{date}_ in _{place}_").format(
                    date=day["date"], place=day["nearest_place"]
                ),
            )
            for day_phase, weather_info in day.items():
                # skip 'date' and 'nearest_place' strings
                if type(weather_info) == str:
                    continue
                temp_str = _(ctx, "Temperature: **{temp}** ˚C").format(
                    temp=weather_info["temp"]
                )
                feel_str = _(ctx, "Feels like: **{feel}** ˚C").format(
                    feel=weather_info["feels_like"]
                )
                wind_str = _(ctx, "Wind speed: **{speed}** km/h").format(
                    speed=weather_info["wind_speed"]
                )
                rain_str = _(ctx, "Chance of rain: **{chance}** %").format(
                    chance=weather_info["rain_chance"]
                )
                info_str = f"""
                    - {temp_str}
                    - {feel_str}
                    - {wind_str}
                    - {rain_str}"""
                embed.add_field(
                    name=day_phase + f": {weather_info['state']}",
                    value=info_str,
                    inline=False,
                )
            embeds.append(embed)

        # create the last "map" embed
        embed = utils.discord.create_embed(
            author=ctx.message.author,
            title=_(ctx, "Weather map for today"),
        )
        img_url = f"https://v3.wttr.in/{name}.png"
        embed.set_image(url=img_url)
        embeds.append(embed)
        return embeds

    @commands.guild_only()
    @commands.check(check.acl)
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
    @commands.check(check.acl)
    @commands.command(name="unset-weather-place")
    async def unset_weather_place(self, ctx):
        """Unset preferred place for weather and forecast information."""
        if Place.remove(ctx.guild.id, ctx.author.id) == 0:
            await ctx.reply(_(ctx, "You don't have any place preference saved."))
            return
        await guild_log.debug(ctx.author, ctx.channel, "Preferred weather place unset.")
        await ctx.reply(_(ctx, "Your preferred weather place was removed."))

    @commands.guild_only()
    @commands.check(check.acl)
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
            _(ctx, "Guild's preferred weather place set to **{place}**.").format(
                place=name
            )
        )

    @commands.guild_only()
    @commands.check(check.acl)
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
        await ctx.reply(_(ctx, "Guild's preferred weather place was removed."))

    @commands.check(check.acl)
    @commands.group(name="weather")
    async def weather(self, ctx, name: Optional[str] = None):
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
        embeds = await self._create_embeds(ctx, name, lang_preference)
        scroll_embed = utils.ScrollableEmbed(ctx, embeds)
        await scroll_embed.scroll()

    def _place_is_valid(self, name: str) -> bool:
        if "&" in name:
            return False
        return True


def setup(bot) -> None:
    bot.add_cog(Weather(bot))
