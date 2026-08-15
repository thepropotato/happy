"""THE WEATHER SERVER: WHAT IT IS DOING NOW, AND WHAT IT IS ABOUT TO DO."""

import sys
from pathlib import Path

# THE SERVER'S OWN FOLDER COMES OFF THE PATH SO A FILE BESIDE THIS ONE CAN NEVER
# BE WHAT SOME LIBRARY'S import FINDS FIRST.
sys.path[0] = str(Path(__file__).resolve().parents[2])

from mcp.server.fastmcp import FastMCP  # noqa: E402

from servers.shared.answering import ok  # noqa: E402
from servers.shared.reaching import Service  # noqa: E402
from servers.weather import meaning, places  # noqa: E402

mcp = FastMCP("weather", log_level="ERROR")

BASE = "https://api.open-meteo.com/v1"

NAME = "Open-Meteo"

# EVERYTHING IS METRIC AND SAYS SO IN ITS OWN FIELD NAME.
CURRENT = (
    "temperature_2m,apparent_temperature,relative_humidity_2m,"
    "precipitation,weather_code,wind_speed_10m"
)

DAILY = (
    "weather_code,temperature_2m_max,temperature_2m_min,"
    "precipitation_sum,precipitation_probability_max"
)

HOURLY = "temperature_2m,precipitation_probability,weather_code"

MOST_DAYS = 16
MOST_HOURS = 48


@mcp.tool()
def get_weather(place: str) -> str:
    """What the weather is doing right now somewhere. Give the place as it was
    said to you — a town, a city, or a city and a country like "Cambridge, UK"
    when the name is a common one.

    Temperatures are Celsius, wind is km/h and rain is millimetres. Say them
    back in whatever units the person asking would use."""
    found = places.located(place)

    got = asked(found, {"current": CURRENT})

    return ok({"place": found["place"], **meaning.now(got.get("current") or {})})


@mcp.tool()
def get_forecast(place: str, days: int = 3) -> str:
    """The next few days somewhere: how warm, how cold, and whether it rains.

    days counts today as the first of them. Temperatures are Celsius and rain is
    millimetres, with the chance of any as a percentage."""
    found = places.located(place)

    answer = asked(found, {"daily": DAILY, "forecast_days": counted(days, MOST_DAYS)})

    return ok({"place": found["place"], "days": meaning.days(answer.get("daily") or {})})


@mcp.tool()
def get_hourly_weather(place: str, hours: int = 12) -> str:
    """Hour by hour from now somewhere, for "will it rain this afternoon" and
    anything else that turns on the time of day rather than on the date.

    Temperatures are Celsius and the chance of rain is a percentage."""
    found = places.located(place)

    answer = asked(found, {"hourly": HOURLY, "forecast_hours": counted(hours, MOST_HOURS)})

    return ok({"place": found["place"], "hours": meaning.hours(answer.get("hourly") or {})})


@mcp.tool()
def find_place(name: str) -> str:
    """Which places answer to a name, for when there is more than one of them and
    you need to ask which was meant. The other tools take a name directly and
    pick the biggest match themselves, so this is only for settling a
    Springfield."""
    return ok([places.spot(each) for each in places.search(name, 5)])


def asked(found, wanted):
    """ONE FORECAST FOR ONE POINT. THE CLOCK IS THE PLACE'S OWN, NOT THIS ONE'S."""
    return Service(BASE, {}, NAME).get(
        "forecast",
        {
            "latitude": found["latitude"],
            "longitude": found["longitude"],
            "timezone": "auto",
            **wanted,
        },
    )


def counted(value, most):
    return max(1, min(int(value), most))


if __name__ == "__main__":
    mcp.run()
