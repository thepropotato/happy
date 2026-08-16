"""HOW HAPPY SOUNDS, ON TOP OF WHAT HE SAYS."""

import re
from pathlib import Path

WORDS = Path(__file__).resolve().parent.parent / "persona.md"

COMMENT = re.compile(r"<!--.*?-->\s*", re.S)

# WHAT brain.persona FALLS BACK TO WHEN IT IS EMPTY, OR SET TO SOMETHING persona.md
# DOES NOT HAVE A SECTION FOR.
DEFAULT = "neutral"

# THE LINE A TONE ENDS ON, WHICH IS SAID AGAIN LATER RATHER THAN ONLY IN THE STANDING PROMPT.
REMINDER = re.compile(r"^> +(.+)$", re.M)

# ONE TONE'S WORDS, THE FIRST TIME THAT TONE IS ASKED FOR.
kept = {}


def parts(tone):
    """THE LONG WORDS AND THE ONE LINE, FOR THE DEFAULT TONE AND ANYTHING UNKNOWN BOTH EMPTY."""
    name = (tone or DEFAULT).strip().lower() or DEFAULT

    if name not in kept:
        kept[name] = divided(written(name))

    return kept[name]


def spoken(tone):
    """THE EXTRA WORDS FOR ONE TONE, WHICH GO AT THE END OF THE STANDING PROMPT."""
    return parts(tone)[0]


def nudge(tone):
    """THE SAME TONE IN ONE LINE, FOR THE END OF A TURN.

    SIXTEEN THOUSAND CHARACTERS OF OPERATIONAL RULES BURY A PERSONALITY NO MATTER HOW LATE IN
    THE PROMPT IT SITS — A MODEL THIS SIZE READS THEM AND ANSWERS LIKE ANY OTHER ASSISTANT.
    THE LAST THING BEFORE IT WRITES IS THE ONE PLACE THE TONE ACTUALLY LANDS."""
    return parts(tone)[1]


def divided(text):
    """A SECTION SPLIT INTO WHAT IS SAID ONCE AND WHAT IS SAID AGAIN."""
    found = REMINDER.search(text)

    if not found:
        return text, ""

    return REMINDER.sub("", text).strip(), found.group(1).strip()


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
