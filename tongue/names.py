"""THE NAME SOMEBODY MEANT, OUT OF THE NAMES THERE ARE.

FOR NAMES THAT ARRIVED BY EAR, WHERE "ZOOKIE" IS A PERSON WRITTEN DOWN AS
"ZOOKIE BHAI" AND SAYING HALF A NAME IS SAYING THE NAME. THIS ANSWERS WITH A
NAME AND WHETHER IT IS SAFE TO USE UNASKED; eyes/matching.py IS A DIFFERENT JOB
WITH A SIMILAR SOUND TO IT, FINDING THE WORDS ON SCREEN TO CLICK, AND IS
STRICTER, BECAUSE CLICKING THE WRONG THING COSTS MORE THAN LOOKING UP THE WRONG
ONE.
"""

import difflib

MATCH_CUTOFF = 0.6
SURE_CUTOFF = 0.85


def shortens(said, name):
    """WHETHER A NAME SAID SHORT IS STILL THIS NAME."""
    at = name.find(said)

    return at == 0 or (at > 0 and name[at - 1] == " ")


def resolve(spoken, known, sure=SURE_CUTOFF):
    """THE CLOSEST KNOWN NAME, AND WHETHER IT IS SAFE TO USE DIRECTLY."""
    lowered = {name.lower(): name for name in known}
    said = spoken.lower().strip()

    if said in lowered:
        return lowered[said], True

    shortened = [name for low, name in lowered.items() if shortens(said, low)]

    if len(shortened) == 1:
        return shortened[0], True

    close = difflib.get_close_matches(said, lowered, n=1, cutoff=MATCH_CUTOFF)

    if not close:
        return (shortened[0], False) if shortened else (None, False)

    ratio = difflib.SequenceMatcher(None, said, close[0]).ratio()

    return lowered[close[0]], ratio >= sure and not shortened
