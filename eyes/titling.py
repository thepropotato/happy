"""WHAT A TAB IS SHOWING WHEN ITS TITLE ONLY SAYS WHICH SITE IT IS ON, READ OFF THE PAGE ITSELF.

NETFLIX CALLS EVERY TAB "Netflix" AND PAINTS ITS PICTURE BLACK TO A SCREENSHOT, BUT ITS OWN PAGE
STILL NAMES THE FILM IN ITS METADATA, AND SO DO MOST PLAYERS AND SHOPS."""

import re
import threading
from urllib.parse import urlparse

import httpx

# A PATH THAT MEANS ONE THING IS BEING WATCHED OR LOOKED AT, RATHER THAN A HOME PAGE.
CONTENT = re.compile(r"/(watch|title|video|videos|detail|details|play|player|movie|movies|episode|episodes|shows?|series|gp/video|dp|p)\b", re.I)

PATIENCE = 4.0

MOST_TITLE = 120

lock = threading.Lock()

# WHAT EACH ADDRESS CALLED ITSELF, SO A TAB IS ASKED ONCE AND NOT ON EVERY LOOK.
known = {}


def named(title, address):
    """THE TAB'S TITLE, OR WHAT ITS PAGE CALLS ITSELF WHEN THE TITLE IS ONLY THE SITE'S NAME."""
    found = resolved(title, address)

    return f"{found} on {title}" if found and title else (found or title)


def resolved(title, address):
    """WHAT THE PAGE CALLS ITSELF, ONLY WHEN THE TITLE IS BARE AND THE ADDRESS IS ONE THING, OR ""."""
    if not bare(title, address) or not CONTENT.search(urlparse(address).path or ""):
        return ""

    found = fetched(address)

    return found if found and found.lower() != (title or "").lower() else ""


def bare(title, address):
    """WHETHER A TITLE SAYS NOTHING BUT THE SITE: "Netflix" ON netflix.com, OR NOTHING AT ALL."""
    words = [word for word in re.split(r"[^a-z0-9]+", (title or "").lower()) if word]
    host = urlparse(address).netloc.lower().removeprefix("www.")

    if not words:
        return True

    return len(words) <= 2 and all(word in host for word in words)


def fetched(address):
    with lock:
        if address in known:
            return known[address]

    found = asked(address)

    # A FETCH THAT FAILED IS NOT AN ANSWER, SO IT IS NOT KEPT AS ONE.
    if found:
        with lock:
            known[address] = found

    return found


def asked(address):
    """THE PAGE'S OWN NAME FOR ITSELF, OFF ITS METADATA, OR "" WHEN IT WILL NOT SAY."""
    from hands.web import embedded
    from hands.web.searching import LIKE_A_BROWSER

    try:
        answer = httpx.get(address, headers=LIKE_A_BROWSER, timeout=PATIENCE, follow_redirects=True)
    except httpx.HTTPError:
        return ""

    if answer.status_code >= 400:
        return ""

    for line in embedded.summary(answer.text).splitlines():
        if line.startswith("Title: "):
            return line[len("Title: "):].strip()[:MOST_TITLE]

    return ""


def showing(browser, title):
    """WHAT THE FRONT TAB OF THIS BROWSER WINDOW IS SHOWING, WHEN THAT IS MORE THAN ITS TITLE, OR "".

    A BROWSER NAMES ITS WINDOW AFTER ITS FRONT TAB, SO THE TAB WITH THIS TITLE IS THE ONE IN FRONT,
    AND ITS ADDRESS IS WHAT THE WINDOW TITLE LEFT OUT."""
    from eyes import tabs

    try:
        open_tabs = tabs.open_now()
    except Exception:
        return ""

    for name, tab, address in open_tabs:
        if name == browser and tab == title:
            return resolved(title, address)

    return ""
