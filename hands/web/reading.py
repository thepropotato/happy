"""ONE PAGE, FETCHED AND READ DOWN TO THE WORDS ON IT.

A RESULT'S SUMMARY DESCRIBES A PAGE RATHER THAN ANSWERING OUT OF IT, SO THE
ANSWER IS ALMOST ALWAYS INSIDE ONE OF THE RESULTS AND SOMETHING HAS TO OPEN IT.
THAT CHOICE BELONGS TO THE MODEL: IT SEARCHES, PICKS THE RESULT THAT LOOKS LIKE
THE ANSWER, READS IT, AND PICKS ANOTHER WHEN THAT ONE WILL NOT HAND ITS TEXT
OVER. NOTHING HERE DECIDES ANYTHING.

FETCHING IS NOT DRIVING. THERE IS NO CLICKING, NO TYPING AND NO SIGNING IN HERE,
AND A PAGE THAT ONLY EXISTS ONCE A SCRIPT HAS RUN SAYS SO PLAINLY INSTEAD OF
COMING BACK AS AN EMPTY ANSWER.
"""

from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from hands.apps.opening import web_address
from hands.web.searching import LIKE_A_BROWSER

# A LITTLE LONGER THAN A SEARCH GETS, BECAUSE A REAL PAGE IS OFTEN A QUARTER OF A
# MEGABYTE. NOT MUCH LONGER: SOME HOSTS TRICKLE A SCRIPT ALONG RATHER THAN REFUSE
# IT, AND THERE ARE FOUR MORE RESULTS BEHIND THIS ONE WORTH GETTING TO.
PATIENCE = 10

# A SEARCH ENGINE WANTS A BROWSER ASKING. A PAGE'S OWN HOST OFTEN WANTS THE
# OPPOSITE: WIKIPEDIA REFUSES ANYTHING WEARING CHROME'S NAME AND ANSWERS AN
# HONEST ONE, BUT ONLY WITH SOMEWHERE TO COMPLAIN TO IN IT. SO WE SAY WHO WE ARE
# FIRST, AND ONLY DRESS UP FOR THE HOSTS THAT TURN THAT AWAY.
AS_OURSELVES = {
    "User-Agent": "Happy/1.0 (+https://github.com/thepropotato/happy)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

TURNED_AWAY = (401, 403, 429)

MOST = 6000

CUT = "\n\n[...cut. Ask again with start set past here to read on.]"

# THE STRUCTURE A PAGE USES TO SAY WHERE ITS OWN CONTENT IS, BEST FIRST.
BODY = ("main", "article", '[role="main"]', "body")

FURNITURE = ("script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg")

# A PAGE HELD BACK STILL ANSWERS 200 AND STILL HAS WORDS ON IT. THESE ARE THEM.
WALLS = (
    "enable javascript",
    "just a moment",
    "checking your browser",
    "access denied",
    "are you a robot",
    "verify you are human",
)

THIN = 200

HELD = "{host} would not hand its text over: {why} Try another result."

NOT_A_PAGE = "{host} answered with {kind}, which is not a page of text."

# A FEED OR AN API IS WORTH READING RAW. A PICTURE OR AN ARCHIVE IS NOT.
TEXTUAL = ("text/", "application/json", "application/xml", "+xml", "+json")


class PageError(Exception):
    pass


def page(url, start=0, most=MOST):
    """WHAT A PAGE ACTUALLY SAYS, AS PLAIN TEXT, FROM start ONWARDS."""
    address = web_address(url)
    answer = fetched(address)
    host = urlhost(address)
    kind = (answer.headers.get("content-type") or "").split(";")[0].strip().lower()

    if kind and not any(each in kind for each in TEXTUAL):
        raise PageError(NOT_A_PAGE.format(host=host, kind=kind))

    words = stripped(answer.text) if "html" in kind or not kind else answer.text.strip()
    wall = walled(words)

    if wall:
        raise PageError(HELD.format(host=host, why=wall))

    window = words[start : start + most]
    more = CUT if len(words) > start + most else ""

    return f"{host}\n\n{window}{more}"


def fetched(address):
    """THE PAGE OFF THE WIRE, ASKED FOR HONESTLY AND THEN THE OTHER WAY."""
    answer = asked(address, AS_OURSELVES)

    if answer.status_code in TURNED_AWAY:
        answer = asked(address, LIKE_A_BROWSER)

    if answer.status_code >= 400:
        raise PageError(
            HELD.format(host=urlhost(address), why=f"it answered {answer.status_code}.")
        )

    return answer


def asked(address, headers):
    """ONE ATTEMPT. WHAT WENT WRONG COMES BACK IN WORDS, BECAUSE IT MAY BE SPOKEN."""
    try:
        return httpx.get(address, headers=headers, timeout=PATIENCE, follow_redirects=True)
    except httpx.TimeoutException:
        raise PageError(HELD.format(host=urlhost(address), why="it took too long to answer."))
    except httpx.HTTPError:
        raise PageError(HELD.format(host=urlhost(address), why="it could not be reached."))


def stripped(html):
    """THE PAGE WITH ITS MENUS, ITS SCRIPTS AND ITS FOOTER TAKEN OFF."""
    page = BeautifulSoup(html, "lxml")

    for tag in page(list(FURNITURE)):
        tag.decompose()

    for where in BODY:
        found = page.select_one(where)

        if found is not None:
            return " ".join(found.get_text(" ", strip=True).split())

    return " ".join(page.get_text(" ", strip=True).split())


def walled(words):
    """WHY THIS IS A DOOR AND NOT A PAGE, OR None WHEN IT IS A PAGE."""
    if not words.strip():
        return "it came back empty."

    low = words[:THIN].lower()

    if any(each in low for each in WALLS):
        return "it wants a real browser with scripts running."

    if len(words) < THIN:
        return "it came back with almost nothing on it."

    return None


def urlhost(address):
    return urlparse(address).netloc.removeprefix("www.") or address
