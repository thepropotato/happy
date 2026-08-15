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

    return BLANK.sub("\n\n", said).strip()
