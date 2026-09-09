"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

import json

import httpx
from langchain_core.tools import tool

from hands.weather import meaning, places

WHERE = "https://api.open-meteo.com/v1/forecast"

PATIENCE = 15

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


@tool
def get_weather(place: str) -> str:
    """What the weather is doing right now somewhere. Give the place as it was
    said to you — a town, a city, or a city and a country like "Cambridge, UK"
    when the name is a common one.

    Temperatures are Celsius, wind is km/h and rain is millimetres. Say them
    back in whatever units the person asking would use."""
    found = places.located(place)
    got = asked(found, {"current": CURRENT})

    return said({"place": found["place"], **meaning.current(got.get("current") or {})})


@tool
def get_forecast(place: str, days: int = 3) -> str:
    """The next few days somewhere: how warm, how cold, and whether it rains.

    days counts today as the first of them. Temperatures are Celsius and rain is
    millimetres, with the chance of any as a percentage."""
    found = places.located(place)
    answer = asked(found, {"daily": DAILY, "forecast_days": counted(days, MOST_DAYS)})

    return said({"place": found["place"], "days": meaning.days(answer.get("daily") or {})})


@tool
def get_hourly_weather(place: str, hours: int = 12) -> str:
    """Hour by hour from now somewhere, for "will it rain this afternoon" and
    anything else that turns on the time of day rather than on the date.

    Temperatures are Celsius and the chance of rain is a percentage."""
    found = places.located(place)
    answer = asked(found, {"hourly": HOURLY, "forecast_hours": counted(hours, MOST_HOURS)})

    return said({"place": found["place"], "hours": meaning.hours(answer.get("hourly") or {})})


@tool
def find_place(name: str) -> str:
    """Which places answer to a name, for when there is more than one of them and
    you need to ask which was meant. The other tools take a name directly and
    pick the biggest match themselves, so this is only for settling a
    Springfield."""
    return said([places.spot(each) for each in places.search(name, 5)])


def asked(found, wanted):
    """ONE FORECAST FOR ONE POINT. THE CLOCK IS THE PLACE'S OWN, NOT THIS ONE'S."""
    answer = httpx.get(
        WHERE,
        params={
            "latitude": found["latitude"],
            "longitude": found["longitude"],
            "timezone": "auto",
            **wanted,
        },
        timeout=PATIENCE,
    )

    if answer.status_code >= 400:
        raise ValueError(f"Open-Meteo would not answer. {answer.status_code}")

    return answer.json() or {}


def said(data):
    return json.dumps(data, default=str, ensure_ascii=False)


def counted(value, most):
    return max(1, min(int(value), most))


TOOLS = [get_weather, get_forecast, get_hourly_weather, find_place]
