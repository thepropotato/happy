"""WHAT A FORECAST MEANS, ONCE IT HAS COME BACK AS NUMBERS."""

# WMO WEATHER CODES. THE NUMBER IS ALL THE FORECAST GIVES AND IS NO USE SPOKEN.
SKIES = {
    0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "freezing fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    56: "freezing drizzle", 57: "heavy freezing drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    66: "freezing rain", 67: "heavy freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "light showers", 81: "showers", 82: "violent showers",
    85: "light snow showers", 86: "snow showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with heavy hail",
}


def now(found):
    return {
        "sky": sky(found.get("weather_code")),
        "temperature_c": found.get("temperature_2m"),
        "feels_like_c": found.get("apparent_temperature"),
        "humidity_percent": found.get("relative_humidity_2m"),
        "rain_mm": found.get("precipitation"),
        "wind_kmh": found.get("wind_speed_10m"),
        "at": found.get("time"),
    }


def days(found):
    return rows(found, day)


def hours(found):
    return rows(found, hour)


def rows(found, shape):
    times = found.get("time") or []

    return [shape(found, at) for at in range(len(times))]


def day(found, at):
    return {
        "date": pick(found, "time", at),
        "sky": sky(pick(found, "weather_code", at)),
        "high_c": pick(found, "temperature_2m_max", at),
        "low_c": pick(found, "temperature_2m_min", at),
        "rain_mm": pick(found, "precipitation_sum", at),
        "rain_chance_percent": pick(found, "precipitation_probability_max", at),
    }


def hour(found, at):
    return {
        "at": pick(found, "time", at),
        "sky": sky(pick(found, "weather_code", at)),
        "temperature_c": pick(found, "temperature_2m", at),
        "rain_chance_percent": pick(found, "precipitation_probability", at),
    }


def pick(found, field, at):
    column = found.get(field) or []

    return column[at] if at < len(column) else None


def sky(code):
    return SKIES.get(code, "unknown") if code is not None else None
