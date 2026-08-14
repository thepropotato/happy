"""THE SEARCH ENGINES, AND THE ONLY FILE THAT KNOWS HOW ONE WRITES ITS PAGE."""

import re
from typing import NamedTuple
from urllib.parse import parse_qs, urlparse


class Result(NamedTuple):
    title: str
    url: str
    summary: str


class Engine(NamedTuple):
    name: str
    url: str
    way: str
    field: str
    read: object


# WHAT A PAGE SERVED INSTEAD OF RESULTS SAYS IN ITS TITLE. ITS STATUS IS STILL 200.
REFUSALS = ("captcha", "verifying your browser", "unusual traffic", "are you a robot")

SPACE = re.compile(r"\s+")

MOST_SUMMARY = 300

MOST_TITLE = 200


def text(part, most=MOST_SUMMARY):
    """WHAT A TAG SAYS, ON ONE LINE, CUT TO SOMETHING WORTH READING."""
    if part is None:
        return ""

    return SPACE.sub(" ", part.get_text(" ", strip=True))[:most]


def direct(href):
    """THE REAL ADDRESS, TAKEN BACK OUT OF THE ENGINE'S OWN CLICK COUNTER."""
    if not href:
        return ""

    if href.startswith("//"):
        href = f"https:{href}"

    wrapped = parse_qs(urlparse(href).query).get("uddg")

    return wrapped[0] if wrapped else href


def blocks(page):
    """THE PAGE WHERE ONE RESULT IS ONE BLOCK, AND AN AD SAYS THAT IT IS AN AD."""
    found = []

    for block in page.select(".result:not(.result--ad):not(.result--no-result)"):
        link = block.select_one(".result__a")

        if link is None:
            continue

        summary = block.select_one(".result__snippet")

        found.append(Result(text(link, MOST_TITLE), direct(link.get("href")), text(summary)))

    return found


def rows(page):
    """THE FLAT TABLE, WHERE A RESULT IS A LINK AND ITS SUMMARY IS THE ROW BELOW."""
    found = []

    for link in page.select("a.result-link"):
        row = link.find_parent("tr")
        summary = row.find_next("td", class_="result-snippet") if row else None

        found.append(Result(text(link, MOST_TITLE), direct(link.get("href")), text(summary)))

    return found


ENGINES = [
    Engine("duckduckgo", "https://html.duckduckgo.com/html/", "POST", "q", blocks),
    Engine("duckduckgo lite", "https://lite.duckduckgo.com/lite/", "POST", "q", rows),
]


def refused(page):
    """WHETHER THIS IS A DOOR BEING HELD SHUT RATHER THAN A PAGE OF RESULTS."""
    title = text(page.title, 100).lower()

    return any(word in title for word in REFUSALS)


def names():
    return ", ".join(each.name for each in ENGINES)
