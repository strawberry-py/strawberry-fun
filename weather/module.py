import urllib.parse
from typing import List, Optional, Tuple

import aiohttp
import discord
import ring
from discord.ext import commands

import pie.database.config
from pie import check, i18n, logger, utils

from .database import Place
from .process import filter_forecast_data, get_day_minmax

translator = i18n.Translator("modules/fun")
_ = translator.translate
guild_log = logger.Guild.logger()
config = pie.database.config.Config.get()
bot_log = logger.Bot.logger()


class Weather(commands.Cog):
    """Weather and forecast"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def __ring_key__(self):
        """Allow ring.lru(), as it requires `self` argument."""
        return "weather"

    @ring.lru(force_asyncio=True)
    async def place_to_geo(self, ctx, place: str) -> Tuple[float, float, str, str]:
        """Use OpenStreetMap Nominatim to translate place to geo coordinates.

        The results are cached in LRU cache.

        :return: Tuple of latitude, longitude, city, country code.
        """
        if not self._is_place_valid(place):
            raise RuntimeError("Place contains illegal characters or is too long.")

        safe_place: str = urllib.parse.quote_plus(place)
        url = (
            "https://nominatim.openstreetmap.org/search"
            f"?city={safe_place}&format=geojson&limit=1&addressdetails=1"
        )
        headers = {
            "User-Agent": f"https://github.com/strawberry-py#bot:{self.bot.user.id}",
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as resp:
                data = await resp.json()

        if not data["features"]:
            raise RuntimeError("Place not found.")

        lon, lat = data["features"][0]["geometry"]["coordinates"]

        city: str
        address = data["features"][0]["properties"]["address"]
        # These keywords are some of the possible values of OpenStreetMap for key:place.
        # I'm not sure if it is possible to trigger more of them; since we are
        # querying the API via '?city=' parameter, this may be all.
        # https://wiki.openstreetmap.org/wiki/Key:place
        for city_kwd in ("city", "town", "village", "hamlet", "isolated_dwelling"):
            if city_kwd in address:
                city = address[city_kwd]
                break
        else:
            city = place
            await bot_log.warning(
                ctx.author,
                ctx.channel,
                f"Did not recognize city keyword for place '{place}': {address}.",
            )
        country = address["country_code"]

        return lat, lon, city, country

    # FIXME Handle 'expires' and 'last-modified' properly.
    #       By only allowing an update once an hour, this should be enough to
    #       more or less follow the Yr.no requirements. We *should* start
    #       handling this when the usage grows above some treshold.
    #       At the time of writing, 'expires' is set to thirty minutes in
    #       a future; so having one hour LRU cache complies with that, even
    #       with ignoring the response headers.
    @ring.lru(expire=60 * 60, force_asyncio=True)
    async def geo_to_forecast(self, ctx, lat: float, lon: float) -> dict:
        """Use yr.no to translate geo coordinates to forecast.

        The results are cached in LRU cache for an hour.

        :return: Result dictionary as per met.no developer documentation.
        """
        url = (
            "https://api.met.no/weatherapi/locationforecast/2.0/complete"
            f"?lat={lat:.4}&lon={lon:.4}"
        )
        headers = {
            "Accept": "application/json",
            "User-Agent": f"https://github.com/strawberry-py#bot:{self.bot.user.id}",
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await bot_log.warning(
                        ctx.author,
                        ctx.channel,
                        f"api.met.no returned error code {resp.status}.",
                    )

                data = await resp.json()

        return data

    def translate_day_phase(self, ctx: commands.Context, day_phase: int) -> str:
        if day_phase == 0:
            return _(ctx, "Night")
        if day_phase == 6:
            return _(ctx, "Morning")
        if day_phase == 12:
            return _(ctx, "Afternoon")
        if day_phase == 18:
            return _(ctx, "Evening")

    def create_embed_list(
        self, ctx, *, place: str, country: str, data: dict
    ) -> List[discord.Embed]:
        embeds: List[discord.Embed] = []

        days = data["data"]
        for day_no, (date, day_data) in enumerate(days.items()):
            if day_no == 0:
                title_date = _(ctx, "Today")
            elif day_no == 1:
                title_date = _(ctx, "Tomorrow")
            elif day_no in (2, 3):
                title_date = date
            else:
                break

            minmax = get_day_minmax(day_data)
            minmax_temp = minmax["air_temperature"]
            if minmax_temp[0] == minmax_temp[1]:
                title = _(ctx, "{date}: {upper} ˚C").format(
                    date=title_date, upper=minmax_temp[0]
                )
            else:
                title = _(ctx, "{date}: {lower} to {upper} ˚C").format(
                    date=title_date, lower=minmax_temp[0], upper=minmax_temp[1]
                )

            embed = utils.discord.create_embed(
                title=title,
                description=_(
                    ctx, "Weather forecast for **{place}, {country}**"
                ).format(place=place, country=country.upper()),
                author=ctx.author,
                footer="met.no & openstreetmap.org",
            )

            for phase, phase_data in day_data.items():
                temperature: str
                if phase_data["air_temperature"][0] != phase_data["air_temperature"][1]:
                    temperature = _(
                        ctx, "Temperature: **{lower} to {upper} ˚C**"
                    ).format(
                        lower=phase_data["air_temperature"][0],
                        upper=phase_data["air_temperature"][1],
                    )
                else:
                    temperature = _(ctx, "Temperature: **{upper} ˚C**").format(
                        upper=phase_data["air_temperature"][1],
                    )

                value = (
                    temperature
                    + "\n"
                    + _(ctx, "Clouds: **{valmax} %**").format(
                        valmax=phase_data["cloudiness"][1],
                    )
                    + "\n"
                    + _(ctx, "Relative humidity: **{valmax} %**").format(
                        valmax=phase_data["relative_humidity"][1],
                    )
                )
                if phase_data["fogginess"][1] > 0:
                    value += "\n" + _(ctx, "Fogginess: **{valmax}**").format(
                        valmax=phase_data["fogginess"][1],
                    )
                embed.add_field(
                    name=self.translate_day_phase(ctx, phase),
                    value=value,
                    inline=False,
                )

            extra_value = (
                _(ctx, "*Air pressure: {valmin} to {valmax} hPa*").format(
                    valmin=minmax["air_pressure"][0],
                    valmax=minmax["air_pressure"][1],
                )
                + "\n"
                + _(ctx, "*Wind speed: up to {valmax} m/s*").format(
                    valmax=minmax["wind_speed"][1],
                )
            )
            if minmax["uv_index"][1] > 0:
                extra_value += "\n" + _(ctx, "*UV index: up to {valmax}*").format(
                    valmax=minmax["uv_index"][1]
                )
            embed.add_field(
                name=_(ctx, "*Extra information*"),
                value=extra_value,
            )

            embeds.append(embed)
        return embeds

    # Input validation

    def _is_place_valid(self, name: str) -> bool:
        for char in ("&", "#", "?"):
            if char in name:
                return False
        if len(name) > 64:
            return False
        return True

    # Commands

    @commands.guild_only()
    @check.acl2(check.ACLevel.MEMBER)
    @commands.command(name="set-weather-place")
    async def set_weather_place(self, ctx, *, name: str):
        """Set preferred place for weather and forecast information."""
        if not self._is_place_valid(name):
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
        if not self._is_place_valid(name):
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
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @check.acl2(check.ACLevel.MEMBER)
    @commands.command(name="weather")
    async def weather(self, ctx, *, place: Optional[str] = None):
        """Get weather information on any place."""
        if place is None:
            # try to get user preference
            place_pref = Place.get(ctx.guild.id, ctx.author.id)
            if place_pref is not None:
                place = place_pref.name
        if place is None:
            # try to get guild preference
            place_pref = Place.get(ctx.guild.id, None)
            if place_pref is not None:
                place = place_pref.name
        if place is None:
            await ctx.reply(_(ctx, "You have to specify a place or set a preference."))
            return

        async with ctx.typing():
            # We need to make 'ctx' ring-hashable. As it does not influence
            # how the function behaves, we can make it static string.
            ctx.__ring_key__ = lambda: "ctx"

            try:
                geo = await self.place_to_geo(ctx, place)
            except RuntimeError:
                await ctx.reply(_(ctx, "Submitted place could not be found."))
                return

            lat, lon, city, country = geo

            try:
                forecast = await self.geo_to_forecast(ctx, lat, lon)
            except aiohttp.ContentTypeError as exc:
                await ctx.reply(_(ctx, "Forecast server refused the geolocation."))
                await bot_log.error(
                    ctx.author,
                    ctx.channel,
                    f"Geolocation refused by api.met.no: {type(exc).__name__}: {exc}.",
                )
                return
            filtered_forecast = filter_forecast_data(forecast)

            embeds = self.create_embed_list(
                ctx, place=city, country=country, data=filtered_forecast
            )

            scroll_embed = utils.ScrollableEmbed(ctx, embeds)
        await scroll_embed.scroll()


async def setup(bot) -> None:
    await bot.add_cog(Weather(bot))
