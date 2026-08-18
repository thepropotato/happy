"""EVERY LIKELY WAY ONE WORD OR NAME MIGHT ACTUALLY BE WRITTEN, FOR WHEN AN EXACT
SEARCH FOR IT FOUND NOTHING. NOT ABOUT FILES OR ANY ONE PLACE — ANY TOOL THAT
SEARCHES BY NAME CAN COME UP EMPTY OVER A CASE, A SPACE OR AN UNDERSCORE THAT
DIFFERS FROM WHAT WAS TYPED, AND THIS IS THE SAME FIX FOR ALL OF THEM."""

import re

from langchain_core.tools import tool

# HOW MANY ARE WORTH OFFERING BACK. PAST THIS IS NOISE, NOT HELP.
MOST = 10

SPLIT = re.compile(r"[\s_\-]+")


def variations(text):
    """EVERY LIKELY SPELLING OF text, ORIGINAL FIRST, NEVER REPEATED."""
    said = (text or "").strip()

    if not said:
        return []

    words = [word for word in SPLIT.split(said) if word]

    made = [
        said,
        said.lower(),
        said.upper(),
        said.title(),
        "_".join(words),
        "_".join(words).lower(),
        "-".join(words),
        "-".join(words).lower(),
        " ".join(words),
        "".join(words),
        "".join(words).lower(),
    ]

    seen, out = set(), []

    for each in made:
        if each and each not in seen:
            seen.add(each)
            out.append(each)

    return out[:MOST]


@tool
def word_variations(text: str) -> str:
    """Every likely spelling of one word or name, to try after an exact search
    for it came back with nothing. Give the exact word or phrase that failed,
    for example "website for venu" or "tax invoice 2026".

    Returns the other ways it might actually be written: upper case, lower
    case, title case, spaces swapped for underscores or hyphens, and with no
    spaces at all. Try the search again with each one in turn before telling
    the person nothing was found.

    Use this as a fallback after find_files, whatsapp_search_contacts, or any
    other tool that searches by name comes back empty. It only varies the
    name you search with — it does not search anything itself, and it is not
    specific to files or to any one tool."""
    said = variations(text)

    if not said:
        return "There was nothing to vary."

    return "\n".join(said)


TOOLS = [word_variations]