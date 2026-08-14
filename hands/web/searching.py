"""ASKING AN ENGINE FOR A PAGE OF RESULTS, AND THE NEXT ONE WHEN IT WILL NOT."""

import httpx
from bs4 import BeautifulSoup

from hands.web import engines

PATIENCE = 8

MOST = 5

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
