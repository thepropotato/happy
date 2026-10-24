"""THE SAVED NAMES CLOSEST TO ONE THAT MATCHED NOTHING."""

import difflib
import re

CLOSE = 0.75

MOST = 3


def words(name):
    return [each for each in re.findall(r"[a-z0-9]+", str(name or "").lower()) if len(each) > 1]


def likeness(asked, name):
    said, saved = words(asked), words(name)

    if not said or not saved:
        return 0.0

    whole = difflib.SequenceMatcher(None, " ".join(said), " ".join(saved)).ratio()

    # A NAME SAID WITH EXTRA WORDS AROUND IT STILL HOLDS EVERY WORD OF THE SAVED ONE.
    each = sum(max(difflib.SequenceMatcher(None, one, other).ratio() for one in said) for other in saved)

    return max(whole, each / len(saved))


def nearest(asked, names):
    """UP TO THREE SAVED NAMES THAT LOOK LIKE asked, CLOSEST FIRST."""
    kept = {str(name).strip() for name in names if name and not str(name).lstrip("+").isdigit()}
    scored = sorted(((likeness(asked, name), name) for name in kept), reverse=True)

    return [name for score, name in scored if score >= CLOSE][:MOST]


def missed(asked, close):
    """WHAT A FAILED LOOKUP SAYS, WITH THE NAMES IT COULD HAVE MEANT."""
    if not close:
        return f"No contact matching '{asked}' was found, so nothing was read, and no saved name is close to it."

    named = ", ".join(f"'{name}'" for name in close)
    closest = f"The closest saved name is {named}" if len(close) == 1 else f"The closest saved names are {named}"

    return (
        f"No contact matching '{asked}' was found, so nothing was read. {closest}. "
        "If one is plainly the same person said differently, call again with it. "
        "If not, ask them which they meant, naming these."
    )
