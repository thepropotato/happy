"""A PLACE SOMEBODY SAID OUT LOUD, TURNED INTO A POINT ON THE EARTH."""

from servers.shared.reaching import Service

BASE = "https://geocoding-api.open-meteo.com/v1"

NAME = "Open-Meteo"


def located(place):
    """ONE PLACE, AS A POINT, OR A REFUSAL NAMING WHAT COULD NOT BE FOUND."""
    wanted = (place or "").strip()

    if not wanted:
        raise ValueError("Say which place. Nothing here knows where anybody is.")

    found = search(wanted, 1)

    if not found:
        raise ValueError(f"There is nowhere called {wanted}.")

    return {
        "place": naming(found[0]),
        "latitude": found[0]["latitude"],
        "longitude": found[0]["longitude"],
    }


def search(name, count):
    found = Service(BASE, {}, NAME).get("search", {"name": name, "count": count})

    return found.get("results") or []


def spot(each):
    return {
        "place": naming(each),
        "latitude": each.get("latitude"),
        "longitude": each.get("longitude"),
        "people": each.get("population"),
    }


def naming(found):
    """A PLACE AS SOMEBODY WOULD SAY IT: THE TOWN, THE REGION, THE COUNTRY."""
    parts = [found.get("name"), found.get("admin1"), found.get("country")]

    return ", ".join(each for each in parts if each)
