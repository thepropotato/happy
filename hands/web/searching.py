"""ASKING AN ENGINE WHAT IT HAS, IN PAGES OR IN PICTURES, AND THE NEXT ONE WHEN IT WILL NOT."""

import re

import httpx
from bs4 import BeautifulSoup

from hands.web import engines

PATIENCE = 8

MOST = 5

# FAR MORE PICTURES THAN ANYONE ASKS FOR, BECAUSE HALF OF ANY PAGE OF THEM REFUSES TO BE FETCHED.
POOL = 60

# DUCKDUCKGO WILL NOT ANSWER ITS PICTURE ENDPOINT WITHOUT A TOKEN OFF ITS OWN SEARCH PAGE.
TOKEN = re.compile(r'vqd="?([\w-]+)"?')

DUCK = "https://duckduckgo.com/"

OPENVERSE = "https://api.openverse.org/v1/images/"

# WE PICK THESE ADDRESSES OURSELVES, SO WHAT COMES BACK HAS TO PROVE IT IS A PICTURE.
ENDINGS = {".jpg", ".png", ".gif", ".webp", ".bmp", ".tif", ".ico", ".svg", ".avif", ".heic"}

# ASKED AS A SCRIPT, AN ENGINE SERVES A DIFFERENT PAGE OR NONE AT ALL.
LIKE_A_BROWSER = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

NOBODY = "No search engine would answer. Tried {names}. {trouble}"


class SearchError(Exception):
    pass


def search(question, most=MOST):
    """WHAT THE FIRST ENGINE THAT WILL ANSWER SAYS, OR NOTHING IF IT KNOWS NONE."""
    question = " ".join((question or "").split())

    if not question:
        raise SearchError("There is nothing to search for.")

    trouble = None

    for engine in engines.ENGINES:
        try:
            found = asked(engine, question)
        except Exception as error:
            trouble = error
            continue

        if found:
            return found[:most]

    if trouble is not None:
        raise SearchError(NOBODY.format(names=engines.names(), trouble=trouble))

    return []


def asked(engine, question):
    """ONE ENGINE'S PAGE, READ INTO RESULTS."""
    sent = {engine.field: question}
    carried = {"data": sent} if engine.way == "POST" else {"params": sent}

    answer = httpx.request(
        engine.way,
        engine.url,
        headers=LIKE_A_BROWSER,
        timeout=PATIENCE,
        follow_redirects=True,
        **carried,
    )

    if answer.status_code >= 400:
        raise SearchError(f"{engine.name} answered {answer.status_code}.")

    page = BeautifulSoup(answer.text, "lxml")

    if engines.refused(page):
        raise SearchError(f"{engine.name} wanted a captcha filled in instead of answering.")

    return engine.read(page)


def pictures(question, most=POOL):
    """THE ADDRESS OF EACH ACTUAL IMAGE, WHICH IS A DIFFERENT INDEX FROM THE ONE search READS."""
    question = " ".join((question or "").split())

    if not question:
        raise SearchError("There is nothing to look for.")

    trouble = None

    for source in (looking, openly):
        try:
            found = source(question, most)
        except Exception as error:
            trouble = error
            continue

        if found:
            return found

    raise SearchError(f"No image search would answer. {trouble or ''}".strip())


def looking(question, most):
    with httpx.Client(headers=LIKE_A_BROWSER, timeout=PATIENCE, follow_redirects=True) as client:
        token = TOKEN.search(client.get(DUCK, params={"q": question}).text)

        if not token:
            raise SearchError("duckduckgo would not hand over a token for its pictures.")

        answer = client.get(
            f"{DUCK}i.js",
            params={"l": "us-en", "o": "json", "q": question, "vqd": token.group(1), "p": "1"},
            headers={"Referer": DUCK},
        )

        if answer.status_code >= 400:
            raise SearchError(f"duckduckgo answered {answer.status_code} for pictures.")

        found = answer.json().get("results", [])[:most]

        return [
            engines.Picture(each["image"], each.get("url", ""))
            for each in found
            if each.get("image")
        ]


def openly(question, most):
    """THE OPENLY LICENSED ONES: NO TOKEN, AND THEY ANSWER WHEN THE OTHER IS BEING DIFFICULT."""
    answer = httpx.get(
        OPENVERSE,
        params={"q": question, "page_size": min(most, 100)},
        headers={"User-Agent": LIKE_A_BROWSER["User-Agent"]},
        timeout=PATIENCE,
        follow_redirects=True,
    )

    if answer.status_code >= 400:
        raise SearchError(f"openverse answered {answer.status_code}.")

    found = answer.json().get("results", [])[:most]

    return [
        engines.Picture(each["url"], each.get("foreign_landing_url", ""))
        for each in found
        if each.get("url")
    ]
