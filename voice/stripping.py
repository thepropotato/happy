"""MARKDOWN TAKEN BACK OUT, SO NOTHING IS READ ALOUD AS A SYMBOL."""

import re

# THE FENCE GOES AND WHAT IT HELD STAYS: DROPPING THE LINES WOULD LOSE WORDS.
FENCE = re.compile(r"^[ \t]*(```+|~~~+).*$", re.M)

HEADING = re.compile(r"^[ \t]*#{1,6}[ \t]+", re.M)

QUOTE = re.compile(r"^[ \t]*>[ \t]?", re.M)

RULE = re.compile(r"^[ \t]*([-*_])(?:[ \t]*\1){2,}[ \t]*$", re.M)

BULLET = re.compile(r"^[ \t]*[-*+][ \t]+", re.M)

NUMBERED = re.compile(r"^[ \t]*\d+[.)][ \t]+", re.M)

IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")

LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")

CODE = re.compile(r"`+([^`]+)`+")

# THE PAIRS, LONGEST FIRST, SO ** IS NEVER READ AS TWO SEPARATE *.
STRONG = re.compile(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1", re.S)

EMPHASIS = re.compile(r"(?<![\w*_])([*_])(?=\S)(.+?)(?<=\S)\1(?![\w*_])", re.S)

STRUCK = re.compile(r"~~(?=\S)(.+?)(?<=\S)~~", re.S)

# A ROW OF A TABLE IS ALL DASHES AND BARS AND SAYS NOTHING OUT LOUD.
DIVIDER = re.compile(r"^[ \t]*\|?[ \t]*:?-{2,}:?[ \t]*(\|[ \t]*:?-{2,}:?[ \t]*)*\|?[ \t]*$", re.M)

EDGE_BARS = re.compile(r"^[ \t]*\||\|[ \t]*$", re.M)

BARS = re.compile(r"[ \t]*\|[ \t]*")

BLANK = re.compile(r"\n{3,}")

# THE MARKS A KEYBOARD NEVER TYPES. THE MODEL READS ONE CHARACTER AT A TIME OFF A TABLE THAT
# COVERS ASCII AND ANSWERS -1 TO EVERY ONE OF THESE, SO AN EM DASH IS NOT A SHORT PAUSE TO IT
# BUT NOTHING AT ALL, AND A CURLY APOSTROPHE IS A HOLE IN THE MIDDLE OF A WORD.
TYPESET = {
    "\u2014": ". ",  # EM DASH, WHICH IS A BREATH WHERE IT IS WRITTEN.
    "\u2013": ", ",  # EN DASH.
    "\u2012": ", ",
    "\u2015": ". ",
    "\u2011": "-",  # A HYPHEN THAT WILL NOT BREAK IS STILL A HYPHEN.
    "\u2010": "-",
    "\u2019": "'",  # THE CURLY QUOTES, WHICH SIT INSIDE WORDS.
    "\u2018": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2026": "... ",  # THE ONE-CHARACTER ELLIPSIS.
    "\u00a0": " ",  # A SPACE THAT WILL NOT BREAK IS STILL A SPACE.
    "\u202f": " ",
    "\u2009": " ",
    "\u200b": "",
}

TYPESET_AT = re.compile("|".join(re.escape(mark) for mark in TYPESET))

# TWO SPACES WHERE A MARK WAS SWAPPED FOR ONE THAT CARRIES ITS OWN.
DOUBLED = re.compile(r"[ \t]{2,}")

# A MARK PUT IN BESIDE ONE THAT WAS ALREADY THERE.
STACKED = re.compile(r"(?<!\.)([,!?;:])[ \t]*[.,]([ \t])")

# A DASH SWAPPED FOR A FULL STOP LEAVES THE NEXT WORD IN LOWER CASE, WHICH IS NOT HOW A
# SENTENCE LOOKS TO ANYTHING READING IT.
OPENING = re.compile(r"(?<=[.!?] )([a-z])")


def spoken(text):
    """ONE SENTENCE AS IT SHOULD SOUND, WITH EVERY MARK THAT ONLY MEANT SOMETHING
    ON A SCREEN TAKEN OUT."""
    said = str(text or "")

    said = FENCE.sub("", said)
    said = RULE.sub("", said)
    said = DIVIDER.sub("", said)
    said = HEADING.sub("", said)
    said = QUOTE.sub("", said)
    said = BULLET.sub("", said)
    said = NUMBERED.sub("", said)

    said = IMAGE.sub(r"\1", said)
    said = LINK.sub(r"\1", said)
    said = CODE.sub(r"\1", said)

    said = STRONG.sub(r"\2", said)
    said = EMPHASIS.sub(r"\2", said)
    said = STRUCK.sub(r"\1", said)

    said = BARS.sub(", ", EDGE_BARS.sub("", said))
    said = typeset(said)

    return BLANK.sub("\n\n", said).strip()


def typeset(said):
    """THE TYPESET MARKS AS THE PLAIN ONES THE VOICE CAN READ. A MARK THE MODEL CANNOT SEE IS
    NOT A SHORTER PAUSE THAN ONE IT CAN, IT IS NO PAUSE AT ALL."""
    said = TYPESET_AT.sub(lambda found: TYPESET[found.group(0)], said)
    said = STACKED.sub(r"\1\2", said)
    said = DOUBLED.sub(" ", said)

    return OPENING.sub(lambda found: found.group(1).upper(), said)
