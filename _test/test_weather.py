import datetime
import json
from pathlib import Path

try:
    # Pure pytest, with `PYTHONPATH=.` as env var
    from weather import process
except ImportError:
    # IDE, like PyCharm
    from modules.fun.weather import process

TIMEZONE = datetime.timezone(datetime.timedelta(hours=1))
"""Timezone used for most examples"""


class Test:
    def request(self, filename: str) -> dict:
        this = Path(__file__)
        with open(this.parent / filename, "r") as handle:
            return json.load(handle)

    def test_split_into_days(self):
        data = self.request("weather-0.json")
        points = data["properties"]["timeseries"]

        result = process.split_into_days(points, timezone=TIMEZONE)
        assert "2022-11-04" in result.keys()
        assert "2022-11-14" in result.keys()
        assert "2022-11-15" not in result.keys()

        assert type(result["2022-11-04"]) is dict
        assert type(result["2022-11-14"]) is dict

        assert "20:00:00" in result["2022-11-04"]
        assert "23:00:00" in result["2022-11-04"]
        assert "01:00:00" in result["2022-11-14"]

    def test_split_into_days_specific(self):
        data = self.request("weather-0.json")
        points = data["properties"]["timeseries"]

        result = process.split_into_days(points, timezone=TIMEZONE)

        expected = {
            "instant": {
                "details": {
                    "air_pressure_at_sea_level": 1015.4,
                    "air_temperature": 16.1,
                    "cloud_area_fraction": 0.0,
                    "cloud_area_fraction_high": 0.0,
                    "cloud_area_fraction_low": 0.0,
                    "cloud_area_fraction_medium": 0.0,
                    "dew_point_temperature": 15.3,
                    "fog_area_fraction": 0.0,
                    "relative_humidity": 94.4,
                    "ultraviolet_index_clear_sky": 0.0,
                    "wind_from_direction": 142.0,
                    "wind_speed": 2.6,
                },
            },
            "next_12_hours": {"summary": {"symbol_code": "clearsky_day"}},
            "next_1_hours": {
                "details": {"precipitation_amount": 0.0},
                "summary": {"symbol_code": "clearsky_night"},
            },
            "next_6_hours": {
                "details": {
                    "air_temperature_max": 24.5,
                    "air_temperature_min": 15.6,
                    "precipitation_amount": 0.0,
                },
                "summary": {"symbol_code": "clearsky_day"},
            },
        }
        assert expected == result["2022-11-05"]["02:00:00"]

    def test_filter_point(self):
        data = self.request("weather-0.json")
        point = data["properties"]["timeseries"][0]["data"]

        result = process.filter_point(point)
        expected = {
            "air_pressure": 1015.2,
            "air_temperature": 21.7,
            "cloudiness": 0.0,
            "fogginess": 0.0,
            "relative_humidity": 47.2,
            "uv_index": 0.0,
            "wind_speed": 2.8,
        }
        assert expected == result

    def test_join_points(self):
        points = self.request("weather-0-filtered.json")

        joined = process.join_points(points)
        print(joined)

        assert {0, 6, 12, 18} == joined.keys()

        assert joined[0]["air_pressure"] == (1015.0, 1018.0)
        assert joined[6]["cloudiness"] == (0.0, 0.8)
        assert joined[12]["relative_humidity"] == (19.1, 31.0)
        assert joined[18]["air_temperature"] == (18.1, 22.9)

    def test_contains_meta(self):
        data = self.request("weather-0.json")

        result = process.filter_forecast_data(data, timezone=TIMEZONE)

        assert "meta" in result
        assert "units" in result["meta"]
        assert "updated_at" in result["meta"]

    def test_contains_filtered_day(self):
        data = self.request("weather-0.json")

        result = process.filter_forecast_data(data, timezone=TIMEZONE)
        assert result["data"]["2022-11-05"][0]["air_temperature"] == (15.6, 17.4)
        assert result["data"]["2022-11-07"][0]["fogginess"] == (0.0, 100.0)
        assert result["data"]["2022-11-07"][6]["fogginess"] == (0.0, 0.0)

    def test_get_daily_minmax(self):
        data = self.request("weather-0-joined.json")["data"]

        result_05 = process.get_day_minmax(data["2022-11-05"])
        assert (15.6, 29.6) == result_05["air_temperature"]
        assert (0.0, 10.9) == result_05["cloudiness"]
        assert (0.0, 9.6) == result_05["uv_index"]

        result_06 = process.get_day_minmax(data["2022-11-06"])
        assert (1013.0, 1018.8) == result_06["air_pressure"]
