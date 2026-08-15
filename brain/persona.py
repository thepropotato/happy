"""HOW HAPPY SOUNDS, ON TOP OF WHAT HE SAYS."""

import re
from pathlib import Path

WORDS = Path(__file__).resolve().parent.parent / "persona.md"

COMMENT = re.compile(r"<!--.*?-->\s*", re.S)

# WHAT brain.persona FALLS BACK TO WHEN IT IS EMPTY, OR SET TO SOMETHING persona.md
# DOES NOT HAVE A SECTION FOR.
DEFAULT = "neutral"

# ONE TONE'S WORDS, THE FIRST TIME THAT TONE IS ASKED FOR.
kept = {}


def spoken(tone):
    """THE EXTRA WORDS FOR ONE TONE. THE DEFAULT TONE, AND ANYTHING UNKNOWN, ADD NOTHING."""
    name = (tone or DEFAULT).strip().lower() or DEFAULT

    if name not in kept:
        kept[name] = written(name)

    return kept[name]


def written(tone):
    """ONE ## SECTION OF persona.md AND NO OTHER.

    THE TONES THAT WERE NOT PICKED ARE WORDS THE MODEL WOULD HAVE TO READ PAST ON EVERY
    TURN, SO THEY ARE NEVER LIFTED OFF THE PAGE AT ALL."""
    try:
        text = WORDS.read_text(encoding="utf-8")
    except OSError:
        return ""

    found = re.search(
        rf"^## +{re.escape(tone)} *$(.*?)(?=^## |\Z)", text, re.M | re.S | re.I
    )

    return COMMENT.sub("", found.group(1)).strip() if found else ""
