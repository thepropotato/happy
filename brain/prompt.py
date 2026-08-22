"""WHAT THE MODEL IS TOLD BEFORE IT HEARS ANYTHING."""

import re
from pathlib import Path

import mcps
from brain import persona
from hands import apps
from memory import routines, settings

WORDS = Path(__file__).resolve().parent.parent / "prompt.md"

HEADING = re.compile(r"^## +([A-Z]+) *$", re.M)

COMMENT = re.compile(r"<!--.*?-->\s*", re.S)

# WHAT FOLLOWS THE STANDING RULES, IN THE ORDER IT IS SAID.
FINISHING_ORDER = ("CORE", "MESSAGING", "BROWSING", "ROUTINES", "REMEMBERING", "CONTACTS")


def written():
    """EVERY ## SECTION OF prompt.md BY NAME. CALLED ONCE, BELOW, AT IMPORT."""
    text = WORDS.read_text(encoding="utf-8")
    marks = list(HEADING.finditer(text))
    ends = [mark.start() for mark in marks[1:]] + [len(text)]

    return {
        mark.group(1): COMMENT.sub("", text[mark.end():end]).strip()
        for mark, end in zip(marks, ends)
    }


SECTIONS = written()

STANDING = SECTIONS["STANDING"]

MACHINE = SECTIONS["MACHINE"]

FINISHING = "\n\n".join(SECTIONS[name] for name in FINISHING_ORDER)

# THE LAST PROMPT COMPOSED, BESIDE THE FACTS IT WAS COMPOSED OUT OF.
composed = None

out_of = None


def system_prompt():
    """THE STANDING PROMPT PLUS THE FACTS ONLY THIS MACHINE CAN SUPPLY."""
    global composed, out_of

    facts = (mcps.mention(), routines.listing(), apps.listing(), settings.get("brain.persona"))

    if composed is not None and facts == out_of:
        return composed

    remote, saved, installed, tone = facts
    parts = [STANDING, FINISHING]

    if remote:
        parts.append(remote)

    if saved:
        parts.append(saved)

    if installed:
        parts.append(f"{MACHINE}\n\n{installed}")

    # LAST, ON PURPOSE — THE CLOSER AN INSTRUCTION SITS TO THE END OF THE PROMPT, THE MORE
    # WEIGHT A MODEL GIVES IT. TONE IS EASY TO BURY UNDER THOUSANDS OF WORDS OF OPERATIONAL
    # RULES, SO IT GOES LAST INSTEAD OF RIGHT AFTER STANDING.
    extra = persona.spoken(tone)

    if extra:
        parts.append(extra)

    composed = "\n\n".join(parts)
    out_of = facts

    return composed