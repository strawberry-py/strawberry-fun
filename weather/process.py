"""
Filter function. Moved from the main module for testing reasons.

The received met.no report contains daily report for at least next three days,
then quarter-day report for next five days. That is too much.
"""
import datetime
import dateutil.parser
from collections import defaultdict
from typing import List, Dict, Tuple


def filter_forecast_data(
    data: dict,
    timezone: datetime.tzinfo = datetime.datetime.now().astimezone().tzinfo,
) -> dict:
    """Filter forecast data."""
    result = {
        "meta": data["properties"]["meta"],
        "data": {},
    }

    days = split_into_days(data["properties"]["timeseries"], timezone=timezone)
    for day, day_values in days.items():
        day_points = {
            time: filter_point(time_data) for time, time_data in day_values.items()
        }
        joined_day_points = join_points(day_points)
        result["data"][day] = joined_day_points

    return result


def split_into_days(
    points: List[dict],
    timezone: datetime.tzinfo = datetime.datetime.now().astimezone().tzinfo,
) -> dict:
    """Split time series into individual days.

    This also converts from UTC to local time.
    """
    result = defaultdict(lambda: {})
    for point in points:
        timestamp = dateutil.parser.parse(point["time"])
        timestamp = timestamp.astimezone(timezone)
        date = timestamp.strftime("%Y-%m-%d")
        time = timestamp.strftime("%H:%M:%S")
        result[date][time] = point["data"]
    return dict(result)


def filter_point(point: dict) -> dict:
    """Filter unnecessary information from an entry."""
    details = point["instant"]["details"]
    result = {
        "air_pressure": details["air_pressure_at_sea_level"],
        "air_temperature": details["air_temperature"],
        "cloudiness": details["cloud_area_fraction"],
        "fogginess": details.get("fog_area_fraction", 0.0),
        "relative_humidity": details["relative_humidity"],
        "uv_index": details.get("ultraviolet_index_clear_sky", 0.0),
        "wind_speed": details["wind_speed"],
    }
    return result


def join_points(points: Dict[str, dict]) -> dict:
    """Join time points into four day sections.

    Returns minimal and maximal value for each of observed values
    for each of time sections.
    """
    pre_result = defaultdict(lambda: defaultdict(lambda: set()))
    for time, data in points.items():
        hour = int(time.split(":", 1)[0])
        round_hour = int(hour // 6) * 6

        for kw, value in data.items():
            pre_result[round_hour][kw].add(value)

    result = defaultdict(lambda: defaultdict(lambda: {}))
    for time, kw_values in pre_result.items():
        for kw, values in kw_values.items():
            values_min = min(values)
            values_max = max(values)
            result[time][kw] = (values_min, values_max)

    return result


def get_day_minmax(day: dict) -> Dict[str, Tuple[float, float]]:
    result = {}
    for _, data in day.items():
        for kw, values in data.items():
            if kw not in result:
                result[kw] = values
            else:
                result[kw] = min(result[kw][0], values[0]), max(
                    result[kw][1], values[1]
                )
    return result
