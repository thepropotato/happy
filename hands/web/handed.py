"""WHICH ADDRESSES THE MODEL MAY OPEN: THE ONES A TOOL HANDED IT, BY NUMBER, AND NOTHING IT WROTE ITSELF."""

import threading
from urllib.parse import urlparse

from memory import conversation

# THE PART OF A PATH THAT PICKS ONE VIDEO OR ONE PRODUCT IS NEVER GUESSABLE, AND IT IS NEVER
# THIS SHALLOW. A SITE'S OWN NAME AND A SECTION OF IT ARE, SO THOSE ARE LET THROUGH.
SHALLOW = 2

REFUSED = (
    "{said} is not an address any tool gave you, so nothing was opened. Never write an "
    "address yourself: search for the thing and use the result's number, so \"2\" opens or "
    "reads the second result."
)

NONE = "There are no results to pick from yet. Search first, then use the number."

lock = threading.Lock()

# THE LATEST LIST OF RESULTS, ONE ADDRESS PER NUMBER, AND EVERY ADDRESS EVER HANDED OVER.
numbered = []
given = set()


def offered(results):
    """A NEW LIST OF RESULTS REPLACES THE NUMBERS AND JOINS THE ADDRESSES."""
    with lock:
        numbered[:] = [each.url for each in results]
        given.update(numbered)


def offer(address):
    """ONE ADDRESS A TOOL FOUND OUTSIDE A SEARCH, FOR EXAMPLE A TAB THAT WAS ALREADY OPEN."""
    with lock:
        given.add(address)


def resolve(said):
    """THE REAL ADDRESS BEHIND WHAT THE MODEL WROTE, OR None AND THE WORDS TO REFUSE IT WITH."""
    said = (said or "").strip()

    if said.isdigit():
        return by_number(int(said))

    address = full(said)

    if address in given or spoken(said) or shallow(address):
        return address, None

    return None, REFUSED.format(said=said)


def by_number(number):
    with lock:
        if not numbered:
            return None, NONE

        if not 1 <= number <= len(numbered):
            return None, f"There are only {len(numbered)} results, so there is no number {number}."

        return numbered[number - 1], None


def spoken(said):
    """WHETHER THE PERSON THEMSELVES SAID THIS ADDRESS THIS TURN."""
    asked = (conversation.asking() or "").lower()
    bare = said.lower().removeprefix("https://").removeprefix("http://").removeprefix("www.").rstrip("/")

    return bool(bare) and bare in asked


def shallow(address):
    """A SITE OR A SECTION OF ONE, WITH NOTHING IN IT THAT ONLY A SEARCH COULD HAVE TOLD YOU."""
    parsed = urlparse(address)
    parts = [each for each in parsed.path.split("/") if each]

    if parsed.query or parsed.fragment or len(parts) > SHALLOW:
        return False

    return all(each.replace("-", "").replace("_", "").isalpha() for each in parts)


def full(said):
    if said.lower().startswith(("http://", "https://")):
        return said

    return "https://" + said.lstrip("/")
