"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

from typing import Literal

from langchain_core.tools import tool

from hands import reasons
from hands.files.finding import folder as chosen
from hands.web import downloading, handed, results
from hands.web.pages import page
from hands.web.searching import ENDINGS, pictures, search

MOST_AT_ONCE = 25

# LOOKING AT ONE AND HAVING THE FILE ARE DIFFERENT ASKS. THIS TOOL ONLY EVER FETCHES; WHAT
# CHANGES IS WHAT IS SAID ABOUT WHAT TO DO NEXT, BECAUSE OPENING IS open_path'S JOB.
SEEING = "show"

KEEPING = "keep"

NEXT = "Now put the first of these in front of them with open_path, by its exact path above."

KEPT = "They asked for the files, so say where they are and leave them shut."


@tool
def search_web(query: str) -> str:
    """Search the web and read back the top results, numbered: a title, the site
    it is on and a line of what the page says.

    Use this whenever the answer is something you do not know or something that
    changes: the news, a score, a price, when a place opens, who somebody is.
    Give it what a person would type into a search box, "weather hyderabad
    tomorrow", not a full sentence. If the results do not answer it, search again
    with different words before giving up.

    The answer is almost always inside one of the results rather than in this
    list, so pick the likeliest and read it with read_page by its number, "2" for
    the second. Asked to show, open, pull up or bring up a thing, searching is only
    the first half: open the likeliest result with open_url and "show", by its
    number, in the same turn.

    This list is yours and nobody else can see it, so never point at it out loud,
    not "the first link" nor any result by position. Open the page or say what it
    said."""
    try:
        found = search(query)
    except Exception as error:
        return reasons.no(f"The search did not go through. {error}")

    return results.written(query, found)


@tool
def read_page(url: str, start: int = 0) -> str:
    """Read a web page and return the words on it as plain text. Give it the
    number of a search result, "2" for the second one, or a site's own name like
    "bbc.com". This is how you get the actual number, date, price or fact:
    search_web finds which page holds it, this one reads it out of that page.

    Nothing is opened on screen and the person sees none of this. If the text
    comes back cut short, call this again with start set to carry on from there.
    If a site will not hand its text over, read the next result down instead, and
    never guess at what a page you could not read said."""
    address, refusal = handed.resolve(url)

    if address is None:
        return reasons.no(refusal)

    try:
        return page(address, start)
    except Exception as error:
        return reasons.no(f"{error}")


@tool
def download_images(description: str, because: Literal[SEEING, KEEPING], count: int = 5,
                    folder: str = "") -> str:
    """Find pictures on the web and save them onto this computer. This is the
    whole job in one call: it looks them up, fetches them and writes the files.

    Use it whenever somebody wants images, pictures, photos, wallpapers, logos or
    mockups downloaded, saved, or put in a folder — "get me ten t-shirt images in
    my downloads" is one call to this and nothing else. Give "description" what a
    person would type into an image search, like "plain white t-shirt mockup".
    "count" is how many they asked for. "folder" is where they land, and left
    empty they go to Downloads.

    Asked to be shown one rather than sent one — show me a picture of her, what
    does that place look like — this fetches it and hands you back where it
    landed, and open_path is what puts it in front of them afterwards. This one
    never opens anything by itself.
    Do not open a stock photo site and leave them to click, and do not use
    search_web, open_url or read_page to hunt for pictures. Those put pages on a
    screen; this is the only thing that puts files on the disk.

    It comes back with the full path of every picture that landed. A picture
    keeps whatever name and ending the site gave it, so never write a path
    yourself to open one afterwards: use the ones this hands back, exactly as
    they are written. Plenty of sites refuse, so this quietly tries more than it
    needs and tells you which ones actually landed."""
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

    # THE NAMES, NOT THE COUNT. A PICTURE COMES DOWN UNDER WHATEVER NAME AND ENDING THE SITE
    # GAVE IT, WHICH IS NEVER THE ONE THAT WOULD BE GUESSED, AND THE NEXT STEP IS ALWAYS TO
    # OPEN ONE: GUESSING LEFT SOMEBODY BEING TOLD A PICTURE WAS ON SCREEN THAT WAS NOT THERE.
    named = "\n".join(f"- {each}" for each in saved)
    said = f"Saved {len(saved)} into {into}.{short} They are:\n{named}"

    # ASKED TO BE SHOWN ONE, BEING TOLD WHERE IT WENT IS THE JOB HANDED BACK, SO IT IS PUT
    # IN FRONT OF THEM HERE AND THE ANSWER SAYS SO. THIS IS THE ONLY THING THAT KNOWS THE
    # NAME IT LANDED UNDER, AND GUESSING THAT NAME IS WHAT WENT WRONG BEFORE.
    return f"{said}\n{NEXT if because == SEEING else KEPT}"


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

    Give it a search result's number, "3" for the third, or the address they
    read out to you. Say where it landed once this has come back, and never say
    something has downloaded before it has."""
    address, refusal = handed.resolve(url)

    if address is None:
        return reasons.no(refusal)

    try:
        into = chosen(folder)
        landed = downloading.save(address, into)
    except Exception as error:
        return reasons.no(f"That did not download: {error}.")

    return f"Saved it as {landed}."


TOOLS = [search_web, read_page, download, download_images]
