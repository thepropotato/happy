"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

from langchain_core.tools import tool

from hands import asking
from hands.web import wording
from hands.web.reading import page
from hands.web.searching import search


@tool
def search_web(query: str) -> str:
    """Search the web and read back the top results: a title, an address and a
    line of what each page says. Use this whenever the answer is something you
    do not already know or something that changes — the news, a score, a price,
    when a place opens, who somebody is, what happened today. Prefer it over
    saying you are not sure or that you cannot check.

    Give it what a person would type into a search box rather than a sentence:
    "weather hyderabad tomorrow", not "could you tell me what the weather will
    be". Put the place and the day in when they matter. If the results do not
    answer it, search again with different words before giving up.

    A result's summary describes a page rather than answering out of it, so the
    answer is almost always inside one of the results and not in this list. Pick
    the result that looks like it holds the answer and read it with read_page.
    Only answer from a summary when it plainly says the whole thing already.

    To put a page in front of the person instead, use open_url. Anything that
    needs clicking, typing or signing in on a site is not this."""
    try:
        found = search(query)
    except Exception as error:
        return asking.no(f"The search did not go through. {error}")

    return wording.written(query, found)


@tool
def read_page(url: str, start: int = 0) -> str:
    """Read a web page and return the words on it as plain text. Takes an
    address from a search result, like "en.wikipedia.org/wiki/Super_Bowl_LX".
    This is how you get the actual number, date, price or fact: search_web finds
    which page holds it, this one reads it out of that page.

    Nothing is opened on screen and the person sees none of this. If the text
    comes back cut short, call this again with start set to carry on from there.

    If a site will not hand its text over, that is one site being difficult, not
    a dead end: go back to the results and read the next one down. Do not give up
    after one page, and never guess at what a page you could not read said."""
    try:
        return page(url, start)
    except Exception as error:
        return asking.no(f"{error}")


TOOLS = [search_web, read_page]
