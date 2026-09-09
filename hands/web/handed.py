"""WHICH ADDRESSES THE MODEL MAY OPEN: THE ONES A TOOL HANDED IT, BY NUMBER, AND NOTHING IT WROTE ITSELF."""

import threading
from urllib.parse import urlparse

from memory import conversation

# A SITE'S OWN NAME IS GUESSABLE AND SO IS ONE ORDINARY WORD OF SECTION AFTER IT. ANYTHING
# THAT PICKS OUT ONE PARTICULAR THING IS NOT, AND THAT IS WHAT A NAME IN A PATH ALWAYS IS.
# THIS WAS TWO SEGMENTS OF ANY LETTERS AT ALL, WHICH LET A CODE HOST'S NAME FOLLOWED BY AN
# INVENTED PROJECT PATH THROUGH: NOBODY HAD SEARCHED FOR IT, THE MODEL ASSEMBLED IT OUT OF
# THE NAME IT WAS ASKED ABOUT, AND IT WAS OPENED AND REPORTED AS THE PAGE THEY WANTED.
SHALLOW = 1

# THIS NAMES THE NEXT STEP, SO IT CARRIES THE MARK THAT KEEPS A TURN ALIVE: WITHOUT IT THE
# REFUSAL COUNTS TOWARDS "ENOUGH SAID NO, STOP", AND A TURN BEING PUT RIGHT ON ITS WAY TO
# DOING THE JOB WOULD BE ENDED FOR BEING PUT RIGHT.
REFUSED = (
    "{said} is not an address any tool gave you, so nothing was opened. Never write an "
    "address yourself: search_web for the thing now, then open the result you want by its "
    "number, so \"2\" opens or reads the second result. This is a step of the job, not a "
    "refusal of it. Do not apologise and do not stop."
)

SEVERAL = (
    "{said} is not an address any tool gave you. Results {numbers} are on {host}: give the "
    "number of the one you mean instead. This is a step of the job, not a refusal of it. "
    "Do not apologise and do not stop."
)

NONE = (
    "There are no results to pick from yet. Call search_web now, then use the number of the "
    "result you want. This is a step of the job, not a refusal of it. Do not apologise and "
    "do not stop."
)

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
    """A SITE OR A SECTION OF ONE, WITH NOTHING IN IT THAT ONLY A SEARCH COULD HAVE TOLD YOU.

    A SECTION IS AN ORDINARY LOWERCASE WORD THE SITE PUT THERE — trending, newest, explore.
    A NAME IS NOT: CAPITALS, DIGITS, HYPHENS AND UNDERSCORES ALL MARK SOMETHING PICKED OUT
    OF MANY, AND THE ONLY WAY TO KNOW IT WAS RIGHT IS TO HAVE BEEN HANDED IT."""
    parsed = urlparse(address)
    parts = [each for each in parsed.path.split("/") if each]

    if parsed.query or parsed.fragment or len(parts) > SHALLOW:
        return False

    return all(each.isalpha() and each.islower() for each in parts)


def full(said):
    if said.lower().startswith(("http://", "https://")):
        return said

    return "https://" + said.lstrip("/")
