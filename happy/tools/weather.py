"""The weather anywhere, from Open-Meteo, which needs no key; with no place named, wherever this computer is."""

from datetime import datetime
from functools import cache
from typing import Annotated

import httpx

from happy.tools import tool

FORECAST = "https://api.open-meteo.com/v1/forecast"
PLACES = "https://geocoding-api.open-meteo.com/v1/search"
SKIES = {0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast", 45: "foggy", 48: "foggy",
         51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 56: "freezing drizzle", 57: "freezing drizzle",
         61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain", 67: "freezing rain",
         71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains", 80: "light showers", 81: "showers",
         82: "heavy showers", 85: "snow showers", 86: "heavy snow showers", 95: "thunderstorms",
         96: "thunderstorms with hail", 99: "thunderstorms with hail"}


@cache
def here():
    """Where this computer is, from its internet address, asked once per run."""
    for url, read in (("https://ipinfo.io/json", lambda d: (d["city"], *map(float, d["loc"].split(",")))),
                      ("http://ip-api.com/json", lambda d: (d["city"], d["lat"], d["lon"]))):
        try:
            return read(httpx.get(url, timeout=5).json())
        except (httpx.HTTPError, KeyError, ValueError):
            continue
    raise ConnectionError("could not work out where this computer is; name the place")


def place(name):
    """(name, latitude, longitude) for a spoken place, the biggest one when several share the name."""
    if not name.strip():
        return here()
    city, _, country = name.partition(",")
    found = httpx.get(PLACES, params={"name": city.strip(), "count": 10}, timeout=8).json().get("results") or []
    if country.strip():
        wanted = country.strip().lower()
        found = [f for f in found if wanted in (f.get("country", "").lower(), f.get("country_code", "").lower(), f.get("admin1", "").lower())] or found
    if not found:
        raise LookupError(f"found no place called {name}")
    best = max(found, key=lambda f: f.get("population") or 0)
    label = ", ".join(part for part in (best["name"], best.get("admin1"), best.get("country")) if part)
    return label, best["latitude"], best["longitude"]


def sky(code):
    return SKIES.get(code, "mixed weather")


def span(said):
    """Which forecast a word for the time means; any wording is taken, since a model writes 'afternoon' as often as 'later today'."""
    said = said.lower().strip()
    if said in ("", "now", "current", "currently", "right now"):
        return "now"
    if "week" in said or "days" in said or "weekend" in said:
        return "this week"
    if "tomorrow" in said:
        return "tomorrow"
    return "later today"


@tool(say="Checking the weather.", label="Weather {when} in {where}")
def weather(where: Annotated[str, "the town or city as said, like 'Cambridge, UK'; empty for where this computer is"] = "",
            when: Annotated[str, "now, later today (this afternoon, tonight), tomorrow, or this week"] = "now"):
    """The weather somewhere: right now, hour by hour for later today, tomorrow, or the next seven days. Temperatures in Celsius."""
    when = span(when)
    try:
        label, lat, lon = place(where)
    except (LookupError, ConnectionError) as error:
        return f"Could not get the weather: {error}."
    params = {"latitude": lat, "longitude": lon, "timezone": "auto"}
    if when == "now":
        params["current"] = "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m"
        params["daily"] = "temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        params["forecast_days"] = 1
    elif when == "later today":
        params["hourly"] = "temperature_2m,precipitation_probability,weather_code"
        params["forecast_hours"] = 24
    else:
        params["daily"] = "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum"
        params["forecast_days"] = 7
    data = httpx.get(FORECAST, params=params, timeout=10).json()
    if data.get("error"):
        return f"Could not get the weather: {data.get('reason')}."
    if when == "now":
        now, day = data["current"], data["daily"]
        return (f"{label}, now: {sky(now['weather_code'])}, {now['temperature_2m']:.0f}°C "
                f"(feels like {now['apparent_temperature']:.0f}°C), humidity {now['relative_humidity_2m']}%, "
                f"wind {now['wind_speed_10m']:.0f} km/h. Today: high {day['temperature_2m_max'][0]:.0f}°C, "
                f"low {day['temperature_2m_min'][0]:.0f}°C, {day['precipitation_probability_max'][0] or 0}% chance of rain.")
    if when == "later today":
        hours = data["hourly"]
        lines = [f"{datetime.fromisoformat(at).strftime('%a %I %p').replace(' 0', ' ')}: {sky(code)}, {temp:.0f}°C, {rain or 0}% rain"
                 for at, temp, rain, code in zip(hours["time"], hours["temperature_2m"], hours["precipitation_probability"], hours["weather_code"])]
        return f"{label}, the next 24 hours (local time there):\n" + "\n".join(lines[::2])
    days = data["daily"]
    lines = []
    for index, (at, code, high, low, chance, total) in enumerate(zip(days["time"], days["weather_code"], days["temperature_2m_max"],
                                                                     days["temperature_2m_min"], days["precipitation_probability_max"], days["precipitation_sum"])):
        name = "Today" if index == 0 else datetime.fromisoformat(at).strftime("%A %d %b").replace(" 0", " ")
        lines.append(f"{name}: {sky(code)}, {low:.0f} to {high:.0f}°C, {chance or 0}% chance of rain" + (f" ({total:.0f} mm)" if total and total >= 0.5 else ""))
    if when == "tomorrow":
        return f"{label}, {lines[1]}"
    return f"{label}, the next seven days:\n" + "\n".join(lines)
