"""WHAT A THING ON THE SCREEN IS CALLED, WHICH THE SCREEN ITSELF NEVER SAYS."""

from eyes.describing import asked

# BIG ENOUGH TO NAME A FACE OR A SKYLINE, WHICH IS FAR SMALLER THAN READING NEEDS. MEASURED:
# THE FULL WIDTH TOOK FIVE TIMES THE PIXELS AND SAID THE SAME THING.
ENOUGH = 640

# WHAT THE LOOKING MODEL IS ASKED, WHICH IS FOR SEARCH WORDS AND NEVER FOR AN ANSWER. A NAME
# IT IS SURE OF IS WORTH HAVING; A DESCRIPTION IS WHAT MAKES THE SEARCH THAT FINDS THE NAME.
DESCRIBE = (
    "This is a picture from a computer screen. Say what is in it in one short line, in words "
    "somebody could type into a search box.\n\n"
    "The text below was read off the same picture by OCR. A title, a channel, a player's "
    "caption or a watermark in it names the thing outright, so use it when it is there.\n\n"
    "{text}\n\n"
    "Say, in this order: what it is from if you can tell (the show, film, game, comic or "
    "place), then who or what is in it (how many, what they look like, what they are wearing "
    "or doing), then the style (live action, anime, cartoon, 3D).\n"
    "Name it only if you are sure. If you are not sure of the name, describe it and do not "
    "guess a name. One line, no more."
)

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

    return asked(small, DESCRIBE.format(text=text[:2000]))


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
