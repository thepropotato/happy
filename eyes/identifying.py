"""WHAT A THING ON THE SCREEN IS CALLED, WHICH THE SCREEN ITSELF NEVER SAYS."""

from eyes import describing

# BIG ENOUGH TO NAME A FACE OR A SKYLINE, WHICH IS FAR SMALLER THAN READING NEEDS. MEASURED:
# THE FULL WIDTH TOOK FIVE TIMES THE PIXELS AND SAID THE SAME THING.
ENOUGH = 640

# HOW SURE THE MODEL SOUNDS. A HEDGE IS THE MODEL SAYING IT DOES NOT KNOW, WHICH IS THE ONE
# THING WORTH GOING TO THE WEB OVER.
HEDGES = (
    "not sure",
    "cannot tell",
    "can't tell",
    "unclear",
    "unable to",
    "i do not know",
    "i don't know",
    "appears to be",
    "possibly",
    "likely",
    "some kind of",
    "unknown",
)


def described(image, text=""):
    """WHAT THE LOOKING MODEL MAKES OF IT, IN WORDS A SEARCH BOX WOULD TAKE.

    THE PICTURE GOES DOWN SMALLER THAN READING WANTS IT. NAMING A FACE OR A SKYLINE TAKES A
    FRACTION OF THE PIXELS THAT READING SMALL PRINT DOES, AND THE FULL WIDTH COST FIVE TIMES
    THE WORK FOR THE SAME ANSWER."""
    small = image.copy()
    small.thumbnail((ENOUGH, ENOUGH))

    return describing.described(small, text[:2000])


def hedged(said):
    """WHETHER THE MODEL STOPPED SHORT OF A NAME, WHICH IS WHEN THE WEB IS WORTH ASKING."""
    low = (said or "").lower()

    return not low.strip() or any(hedge in low for hedge in HEDGES)


def corroborated(image):
    """WHERE ELSE THIS PICTURE APPEARS, WHICH SOMETIMES NAMES IT AND OFTEN DOES NOT."""
    from hands.web.matching import matched  # LATE: eyes REACHES ACROSS INTO hands.

    try:
        return matched(image)
    except Exception:
        # AN ENGINE REFUSING IS NOT A FAILURE OF THE ANSWER, ONLY OF ITS SECOND OPINION.
        return []
