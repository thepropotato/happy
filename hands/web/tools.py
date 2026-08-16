"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

from langchain_core.tools import tool

from hands import reasons
from hands.files.finding import folder as chosen
from hands.web import downloading, results
from hands.web.pages import page
from hands.web.searching import ENDINGS, pictures, search

MOST_AT_ONCE = 25


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


@tool
def download_images(description: str, count: int = 5, folder: str = "") -> str:
    """Find pictures on the web and save them onto this computer. This is the
    whole job in one call: it looks them up, fetches them and writes the files.

    Use it whenever somebody wants images, pictures, photos, wallpapers, logos or
    mockups downloaded, saved, or put in a folder — "get me ten t-shirt images in
    my downloads" is one call to this and nothing else. Give "description" what a
    person would type into an image search, like "plain white t-shirt mockup".
    "count" is how many they asked for. "folder" is where they land, and left
    empty they go to Downloads.

    Do not open a stock photo site and leave them to click, and do not use
    search_web, open_url or read_page to hunt for pictures. Those put pages on a
    screen; this is the only thing that puts files on the disk. Plenty of sites
    refuse to hand a picture over, so this quietly tries more than it needs and
    tells you how many actually landed."""
    wanted = max(1, min(int(count or 1), MOST_AT_ONCE))

    try:
        into = chosen(folder)
        found = pictures(description)
    except Exception as error:
        return reasons.no(f"{error}")

    if not found:
        return reasons.no(f"Nothing came back for {description}.")

    saved, refused = downloading.gather(found, into, wanted, description, ENDINGS)

    if not saved:
        return reasons.no(f"Every one of the {refused} pictures I tried refused to be downloaded.")

    short = f" That is all {description} that would be handed over." if len(saved) < wanted else ""

    return f"Saved {len(saved)} pictures into {into}.{short}"


@tool
def download(url: str, folder: str = "") -> str:
    """Save whatever is at a web address onto this computer: a picture, a PDF, a
    song, a video, a spreadsheet, an installer, a zip. Anything an address hands
    over, this writes to the disk under the name it came with.

    Use this the moment somebody wants a copy of something rather than a look at
    it — download this, save that, get me the file, put it in my downloads. Use it
    for an address they read out to you and for one a tool just gave you alike.
    Use download_images instead when they want pictures found for them rather
    than one they already have the address of. "folder" is where it lands, and
    left empty it goes to Downloads.

    Never make an address up: use the one they said or the one a tool handed you.
    Say where it landed once this has come back, and never say something has
    downloaded before it has."""
    try:
        into = chosen(folder)
        landed = downloading.save(url, into)
    except Exception as error:
        return reasons.no(f"That did not download: {error}.")

    return f"Saved it as {landed}."


TOOLS = [search_web, read_page, download, download_images]
