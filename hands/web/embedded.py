"""THE FACTS A SCRIPT-DRAWN PAGE STILL SHIPS INSIDE ITS HTML, READ WITHOUT RUNNING ANY SCRIPT."""

import json
import re

from bs4 import BeautifulSoup

# WHERE YOUTUBE PUTS THE VIDEO'S OWN DETAILS, VIEWS INCLUDED, ON EVERY WATCH PAGE.
PLAYER = re.compile(r"ytInitialPlayerResponse\s*=\s*")

# WHERE A CHANNEL, SEARCH OR PLAYLIST PAGE PUTS ITS LIST, NEWEST FIRST ON THE VIDEOS TAB.
LISTING = re.compile(r"ytInitialData\s*=\s*")

# HOW MANY OF THAT LIST ARE WORTH SAYING; THE ANSWER IS ALWAYS NEAR THE TOP.
MOST_LISTED = 15

META = ("og:title", "og:description", "description", "og:site_name")

# THE FIELDS WORTH SAYING OUT OF STRUCTURED DATA, AND WHAT TO CALL EACH.
SAID = (
    ("name", "Title"), ("headline", "Title"), ("description", "About"),
    ("datePublished", "Published"), ("uploadDate", "Published"), ("duration", "Length"),
)

MOST_ABOUT = 400


def summary(html):
    """WHAT THE PAGE SAYS ABOUT ITSELF, AS LINES, OR "" WHEN IT SAYS NOTHING USEFUL."""
    lines = video(html) or listed(html) or structured(html)

    if not lines:
        lines = tags(html)

    return "\n".join(dict.fromkeys(line for line in lines if line))


def video(html):
    """A YOUTUBE WATCH PAGE: TITLE, CHANNEL, VIEWS, LENGTH AND THE FIRST WORDS OF ITS BLURB."""
    found = PLAYER.search(html)

    if not found:
        return []

    data = balanced(html, found.end())

    if not data:
        return []

    details = data.get("videoDetails") or {}

    if not details:
        return []

    seconds = int(details.get("lengthSeconds") or 0)

    return [
        f"Title: {details.get('title', '')}",
        f"Channel: {details.get('author', '')}",
        f"Views: {views(details.get('viewCount'))}",
        f"Length: {seconds // 60} minutes {seconds % 60} seconds" if seconds else "",
        f"About: {short(details.get('shortDescription', ''))}",
    ]


def listed(html):
    """A CHANNEL OR SEARCH PAGE: THE VIDEOS IT LISTS, IN THE ORDER IT LISTS THEM."""
    found = LISTING.search(html)

    if not found:
        return []

    data = balanced(html, found.end())

    if not data:
        return []

    videos = [said for card in lockups(data) if (said := lockup(card))]

    if not videos:
        return []

    return ["Videos, newest first:"] + videos[:MOST_LISTED]


def lockups(data):
    """EVERY VIDEO CARD IN THE PAGE'S OWN DATA, IN PAGE ORDER."""
    found = []

    def walk(node):
        if isinstance(node, dict):
            if "lockupViewModel" in node:
                found.append(node["lockupViewModel"])

            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)

    return found


def lockup(card):
    """ONE CARD AS A LINE: TITLE, THEN THE VIEWS AND AGE IT SHOWS UNDERNEATH."""
    inner = (card.get("metadata") or {}).get("lockupMetadataViewModel") or {}
    title = (inner.get("title") or {}).get("content") or ""

    if not title:
        return ""

    rows = ((inner.get("metadata") or {}).get("contentMetadataViewModel") or {}).get("metadataRows") or []
    parts = [
        (part.get("text") or {}).get("content") or ""
        for row in rows for part in row.get("metadataParts") or []
    ]
    said = ", ".join(part for part in parts if part)

    return f"- {title}" + (f" ({said})" if said else "")


def structured(html):
    """JSON-LD: THE PRODUCT, ARTICLE OR VIDEO A PAGE DECLARES ITSELF TO BE."""
    page = BeautifulSoup(html, "lxml")
    lines = []

    for block in page.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(block.string or "")
        except ValueError:
            continue

        for item in data if isinstance(data, list) else [data]:
            lines += described(item)

    return lines


def described(item):
    if not isinstance(item, dict):
        return []

    if "@graph" in item:
        return [line for each in item["@graph"] for line in described(each)]

    lines = [f"{label}: {short(str(item[key]))}" for key, label in SAID if item.get(key)]
    offer = item.get("offers")

    if isinstance(offer, list):
        offer = offer[0] if offer else None

    if isinstance(offer, dict) and offer.get("price"):
        lines.append(f"Price: {offer.get('price')} {offer.get('priceCurrency', '')}".strip())

    rating = item.get("aggregateRating")

    if isinstance(rating, dict) and rating.get("ratingValue"):
        lines.append(f"Rating: {rating['ratingValue']} from {rating.get('ratingCount') or rating.get('reviewCount', '?')} ratings")

    for stat in item.get("interactionStatistic") or []:
        if isinstance(stat, dict) and stat.get("userInteractionCount"):
            kind = str(stat.get("interactionType", "")).rsplit("/", 1)[-1].removesuffix("Action")
            lines.append(f"{kind or 'Interactions'}: {views(stat['userInteractionCount'])}")

    return lines


def tags(html):
    """THE OPEN GRAPH AND DESCRIPTION TAGS, WHICH NEARLY EVERY PAGE CARRIES."""
    page = BeautifulSoup(html, "lxml")
    lines = []

    for name in META:
        tag = page.find("meta", attrs={"property": name}) or page.find("meta", attrs={"name": name})

        if tag and tag.get("content"):
            label = "About" if "description" in name else name.split(":")[-1].replace("_", " ").title()
            lines.append(f"{label}: {short(tag['content'])}")

    return lines


def balanced(text, start):
    """THE JSON OBJECT THAT OPENS AT start, FOUND BY COUNTING BRACES, OR None."""
    if start >= len(text) or text[start] != "{":
        return None

    depth = 0
    quoted = False
    escaped = False

    for index in range(start, len(text)):
        char = text[index]

        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1

            if depth == 0:
                try:
                    return json.loads(text[start:index + 1])
                except ValueError:
                    return None

    return None


def views(count):
    try:
        return f"{int(count):,}"
    except (TypeError, ValueError):
        return str(count or "")


def short(said):
    said = " ".join(str(said).split())

    return said if len(said) <= MOST_ABOUT else said[:MOST_ABOUT].rstrip() + "..."
