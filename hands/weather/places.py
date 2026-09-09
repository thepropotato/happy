"""A PLACE SOMEBODY SAID OUT LOUD, TURNED INTO A POINT ON THE EARTH."""

import httpx

WHERE = "https://geocoding-api.open-meteo.com/v1/search"

PATIENCE = 15


def located(place):
    """ONE PLACE, AS A POINT, OR A REFUSAL NAMING WHAT COULD NOT BE FOUND."""
    wanted = (place or "").strip()

    if not wanted:
        raise ValueError("Say which place. Nothing here knows where anybody is.")

    found = search(wanted, 1)

    # THE GEOCODER TAKES A TOWN AND NOTHING ELSE: "Hyderabad, India" HAPPENS TO WORK AND
    # "Cambridge, UK" FINDS NOTHING AT ALL, BECAUSE IT CANNOT READ AN ABBREVIATION. THE
    # QUALIFIER IS WHAT SOMEBODY SAYS TO TELL TWO TOWNS APART, SO IT IS TAKEN OFF AND USED
    # TO PICK BETWEEN WHAT THE BARE NAME FINDS.
    if not found and "," in wanted:
        town, _, qualifier = wanted.partition(",")
        found = narrowed(search(town.strip(), 10), qualifier.strip())

    if not found:
        raise ValueError(f"There is nowhere called {wanted}.")

    return {
        "place": naming(found[0]),
        "latitude": found[0]["latitude"],
        "longitude": found[0]["longitude"],
    }


def narrowed(found, qualifier):
    """THE ONES WHOSE COUNTRY, CODE OR REGION IS WHAT SOMEBODY SAID AFTER THE COMMA."""
    wanted = qualifier.lower()

    if not wanted:
        return found

    matched = [
        each
        for each in found
        if wanted
        in {
            str(each.get("country") or "").lower(),
            str(each.get("country_code") or "").lower(),
            str(each.get("admin1") or "").lower(),
        }
    ]

    # "UK" IS NOT THE COUNTRY'S NAME NOR ITS CODE, SO THE COMMON SHORTHANDS ARE SPELLED OUT.
    if not matched:
        spelled = SHORTHAND.get(wanted)

        if spelled:
            matched = [
                each
                for each in found
                if str(each.get("country_code") or "").lower() == spelled
            ]

    return matched


# WHAT PEOPLE SAY OUT LOUD FOR A COUNTRY, AGAINST THE CODE THE GEOCODER ANSWERS WITH.
SHORTHAND = {
    "uk": "gb",
    "u.k.": "gb",
    "britain": "gb",
    "england": "gb",
    "us": "us",
    "u.s.": "us",
    "usa": "us",
    "america": "us",
    "uae": "ae",
}


def search(name, count):
    answer = httpx.get(WHERE, params={"name": name, "count": count}, timeout=PATIENCE)

    if answer.status_code >= 400:
        raise ValueError(f"Open-Meteo would not look that up. {answer.status_code}")

    return (answer.json() or {}).get("results") or []


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
