"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

from langchain_core.tools import tool

from hands import reasons
from hands.web import results
from hands.web.pages import page
from hands.web.searching import search


@tool
def search_web(query: str) -> str:
    """Search the web and read back the top results: a title, an address and a
    line of what each page says.

    Use this whenever the answer is something you do not know or something that
    changes — the news, a score, a price, when a place opens, who somebody is.
    Prefer it over saying you are not sure or cannot check. Give it what a
    person would type into a search box: "weather hyderabad tomorrow", not a
    full sentence. If the results do not answer it, search again with different
    words before giving up.

    The answer is almost always inside one of the results rather than in this
    list, because a summary describes a page instead of answering out of it. So
    pick the likeliest result and read it with read_page. Answer from a summary
    only when it plainly says the whole thing.

    To put a page in front of the person instead, use open_url."""
    try:
        found = search(query)
    except Exception as error:
        return reasons.no(f"The search did not go through. {error}")

    return results.written(query, found)


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
        return reasons.no(f"{error}")


TOOLS = [search_web, read_page]
