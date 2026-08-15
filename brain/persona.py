"""HOW HAPPY SOUNDS, ON TOP OF WHAT HE SAYS."""

import re
from pathlib import Path

WORDS = Path(__file__).resolve().parent.parent / "persona.md"

HEADING = re.compile(r"^## +([A-Z]+) *$", re.M)

COMMENT = re.compile(r"<!--.*?-->\s*", re.S)

# WHAT brain.persona FALLS BACK TO WHEN IT IS EMPTY, OR SET TO SOMETHING persona.md
# DOES NOT HAVE A SECTION FOR.
DEFAULT = "neutral"


def written():
    """EVERY TONE persona.md OFFERS, KEYED BY ITS LOWERCASE NAME. CALLED ONCE, AT IMPORT."""
    text = WORDS.read_text(encoding="utf-8")
    marks = list(HEADING.finditer(text))
    ends = [mark.start() for mark in marks[1:]] + [len(text)]

    return {
        mark.group(1).lower(): COMMENT.sub("", text[mark.end():end]).strip()
        for mark, end in zip(marks, ends)
    }


TONES = written()


def spoken(tone):
    """THE EXTRA WORDS FOR ONE TONE. THE DEFAULT TONE, AND ANYTHING UNKNOWN, ADD NOTHING."""
    return TONES.get((tone or DEFAULT).strip().lower(), "")