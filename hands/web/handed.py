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

SEVERAL = (
    "{said} is not an address any tool gave you. Results {numbers} are on {host}: give the "
    "number of the one you mean instead."
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

    return by_site(address, said)


def by_site(address, said):
    """AN ADDRESS MADE UP ON A SITE THE RESULTS ACTUALLY HAVE MEANS THAT RESULT, AND IS GIVEN
    IT WHEN THERE IS ONLY ONE. TWO OR MORE IS A CHOICE THE MODEL HAS TO MAKE BY NUMBER."""
    host = urlparse(address).netloc.removeprefix("www.").lower()

    with lock:
        matching = [number for number, each in enumerate(numbered, 1)
                    if urlparse(each).netloc.removeprefix("www.").lower() == host]
        found = [numbered[number - 1] for number in matching]

    if len(found) == 1:
        return found[0], None

    if found:
        return None, SEVERAL.format(said=said, host=host, numbers=", ".join(map(str, matching)))

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
