import aiohttp
import urllib.parse
from typing import Optional, List, Tuple

import ring

import discord
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
    async def place_to_geo(self, place: str) -> Tuple[float, float, str, str]:
        """Use OpenStreetMap Nominatim to translate place to geo coordinates.

        The results are cached in LRU cache.

        :return: Tuple of latitude, longitude, city, country code.
        """
        safe_place: str = urllib.parse.quote_plus(place)
        url = (
            "https://nominatim.openstreetmap.org/search"
            f"?city={safe_place}&format=geojson&limit=1&addressdetails=1"
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()

        lat, lon = data["features"][0]["geometry"]["coordinates"]

        city: str
        address = data["features"][0]["properties"]["address"]
        for city_kwd in ("city", "town", "village"):
            if city_kwd in address:
                city = address[city_kwd]
        country = address["country_code"]

        return lat, lon, city, country

    @ring.lru(expire=60 * 60, force_asyncio=True)
    async def geo_to_forecast(self, lat: float, lon: float) -> dict:
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
            "User-Agent": f"https://github.com/pumpkin-py#bot:{self.bot.user.id}",
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as resp:
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
                title = f"{title_date}: {minmax_temp[0]} ˚C"
            else:
                title = f"{title_date}: {minmax_temp[0]} - {minmax_temp[1]} ˚C"

            embed = utils.discord.create_embed(
                title=title,
                description=_(
                    ctx, "Weather forecast for **{place}, {country}**"
                ).format(place=place, country=country.upper()),
                author=ctx.author,
                footer="met.no & openstreetmap.org",
            )

            for phase, phase_data in day_data.items():
                value = (
                    _(ctx, "Temperature: **{valmin} - {valmax} ˚C**").format(
                        valmin=phase_data["air_temperature"][0],
                        valmax=phase_data["air_temperature"][1],
                    )
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
                _(ctx, "*Air pressure: {valmin} - {valmax} hPa*").format(
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
            geo = await self.place_to_geo(place)
            lat, lon, city, country = geo
            forecast = await self.geo_to_forecast(lat, lon)
            filtered_forecast = filter_forecast_data(forecast)

            embeds = self.create_embed_list(
                ctx, place=city, country=country, data=filtered_forecast
            )

            scroll_embed = utils.ScrollableEmbed(ctx, embeds)
        await scroll_embed.scroll()


async def setup(bot) -> None:
    await bot.add_cog(Weather(bot))
