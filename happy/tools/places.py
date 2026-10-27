"""Towns found by how they sound, and by a web search when they sound like nothing, so a misheard name still finds the town."""

import io
import re
import unicodedata
import zipfile
from collections import Counter
from difflib import SequenceMatcher
from functools import cache

import httpx

from happy import paths

DUMP = "https://download.geonames.org/export/dump/"
FOLDER = paths.HOME / "places"
ALIASES = {"uk": "United Kingdom", "britain": "United Kingdom", "usa": "United States", "us": "United States",
           "america": "United States", "uae": "United Arab Emirates"}
NOISE = {"currently", "now", "today", "right", "outside", "at", "the", "moment", "please", "in", "like"}
SURE = 0.9


def flat(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", text)


def sound(text):
    """A spelling-blind key, so the ways one name can be heard and written come out nearly the same."""
    text = flat(text)
    for a, b in (("ph", "f"), ("w", "v"), ("ee", "i"), ("oo", "u"), ("y", "i"), ("z", "s"), ("q", "k"), ("ck", "k"), ("c", "k")):
        text = text.replace(a, b)
    text = re.sub(r"([bdfgjklmnprstvx])h", r"\1", text)
    return re.sub(r"(.)\1+", r"\1", text)


def like(a, b):
    return SequenceMatcher(None, a, b).ratio()


def fetch(name):
    """One GeoNames file, downloaded the first time a name is not found exactly."""
    path = FOLDER / name.replace(".zip", ".txt")
    if not path.exists():
        FOLDER.mkdir(parents=True, exist_ok=True)
        data = httpx.get(DUMP + name, timeout=60, follow_redirects=True).raise_for_status().content
        if name.endswith(".zip"):
            data = zipfile.ZipFile(io.BytesIO(data)).read(path.name)
        path.write_bytes(data)
    return path.read_text(encoding="utf-8")


@cache
def gazetteer():
    """Every town of 5,000 or more people with its other spellings, the states and countries they sit in, and each spelling's town."""
    regions = dict(line.split("\t")[:2] for line in fetch("admin1CodesASCII.txt").splitlines() if line)
    countries = {p[0]: p[4] for p in (line.split("\t") for line in fetch("countryInfo.txt").splitlines() if line and not line.startswith("#"))}
    towns = []
    for line in fetch("cities5000.zip").splitlines():
        p = line.split("\t")
        others = {sound(n) for n in (p[2], *p[3].split(",")) if n.isascii() and flat(n)}
        towns.append({"name": p[1], "region": regions.get(f"{p[8]}.{p[10]}", ""), "country": countries.get(p[8], ""),
                      "lat": float(p[4]), "lon": float(p[5]), "people": int(p[14] or 0), "own": sound(p[1]), "keys": others | {sound(p[1])}})
    areas = {sound(n): n for n in (*regions.values(), *countries.values())} | {sound(k): v for k, v in ALIASES.items()}
    # A SUBURB THAT LISTS THE CITY AS ANOTHER NAME LOSES TO THE CITY ITSELF, SO A TOWN'S OWN NAME IS FILED LAST.
    spelled = {}
    for own in (False, True):
        for town in sorted(towns, key=lambda t: t["people"]):
            for key in ({town["own"]} if own else town["keys"]):
                spelled[key] = town
    return towns, areas, spelled


def area(words, areas):
    """The trailing words that name a state or country, and the words left over for the town."""
    for k in (3, 2, 1):
        if len(words) > k:
            key = sound("".join(words[-k:]))
            # A WORD THAT BEGINS A STATE OR COUNTRY NAME MEANS THAT ONE, BEFORE ANY NAME IT MERELY RESEMBLES.
            begun = [a for a in areas if len(key) >= 5 and a.startswith(key)]
            best = min(begun, key=len) if begun else max(areas, key=lambda a: like(key, a))
            if begun or like(key, best) >= 0.85:
                return areas[best], words[:-k]
    return "", words


def closest(key, towns, region):
    """(how alike, town) for the town that sounds most like the key, or (0, None)."""
    scored = []
    for town in towns:
        if region and region not in (town["region"], town["country"]):
            continue
        best = 0
        for other in town["keys"]:
            if other[:1] != key[:1] or abs(len(other) - len(key)) > max(3, len(key) // 3):
                continue
            matcher = SequenceMatcher(None, key, other)
            if matcher.real_quick_ratio() >= 0.75 and matcher.quick_ratio() >= 0.75:
                best = max(best, matcher.ratio())
        if best >= 0.75:
            scored.append((best, town))
    if not scored:
        return 0, None
    top = max(score for score, _ in scored)
    near = [town for score, town in scored if score >= top - 0.05]
    return top, max(near, key=lambda t: (like(key, t["own"]) >= top - 0.05, t["people"]))


def words_of(said):
    words = [w for w in re.split(r"[\s,]+", said.lower()) if w]
    while words and words[-1] in NOISE:
        words.pop()
    return words


def heard(said):
    """(how alike, town) by sound alone, with a trailing state or country taken as where to look only when that fits better."""
    words = words_of(said)
    if not words:
        return 0, None
    towns, areas, _ = gazetteer()
    region, rest = area(words, areas)
    whole = closest(sound("".join(words)), towns, "")
    if region and rest:
        narrowed = closest(sound("".join(rest)), towns, region)
        if narrowed[0] >= whole[0]:
            return narrowed
    return whole


def searched(said):
    """The town a web search takes the name to: a name in the results that is a real town and sounds a little like what was said."""
    from happy.tools import web

    words = words_of(said)
    if not words:
        return None
    _, areas, spelled = gazetteer()
    region, rest = area(words, areas)
    whole, part = sound("".join(words)), sound("".join(rest))
    overview, found = web.search(" ".join(words) + " city")
    seen = Counter()
    # GOOGLE'S OVERVIEW NAMES THE PLACE IT THINKS WAS MEANT, SO ITS NAMES COUNT THRICE, TITLES TWICE, SNIPPETS ONCE.
    for text, weight in [(overview, 3)] + [(r.get("title", ""), 2) for r in found] + [(r.get("body", ""), 1) for r in found]:
        for run in re.findall(r"[^\W\d_][^\W\d_'-]*(?:\s+[^\W\d_][^\W\d_'-]*){0,2}", text):
            names = run.split()
            for size in range(len(names), 0, -1):
                for start in range(len(names) - size + 1):
                    phrase = " ".join(names[start:start + size])
                    if phrase[:1].isupper() and sound(phrase) in spelled:
                        seen[sound(phrase)] += weight
    best, top = None, 0
    for spelling, count in seen.items():
        town = spelled[spelling]
        inside = region and region in (town["region"], town["country"])
        fit = like(part, spelling) if inside else like(whole, spelling)
        # A NAME THE RESULTS ARE FULL OF THAT SOUNDS LITTLE LIKE WHAT WAS SAID IS SOME OTHER PLACE.
        if fit < 0.7:
            continue
        score = count * fit * (2 if inside else 1)
        if score > top:
            best, top = town, score
    return best


def label(town):
    return ", ".join(part for part in (town["name"], town["region"], town["country"]) if part), town["lat"], town["lon"]


def guess(said):
    """(name, latitude, longitude) for the town meant: by sound when it is clear, else from a web search, else the nearest sound; or None."""
    score, town = heard(said)
    if town and score >= SURE:
        return label(town)
    try:
        found = searched(said)
    except Exception:
        found = None
    if found:
        return label(found)
    return label(town) if town else None


def nearest(lat, lon):
    """(name, latitude, longitude) of the town a point is in: the biggest within a few kilometres of the nearest, so a suburb gives its city."""
    import math

    towns, _, _ = gazetteer()
    squash = math.cos(math.radians(lat))
    away = {id(t): 111 * math.hypot(t["lat"] - lat, (t["lon"] - lon) * squash) for t in towns}
    closest = min(away.values())
    return label(max((t for t in towns if away[id(t)] <= closest + 5), key=lambda t: t["people"]))
