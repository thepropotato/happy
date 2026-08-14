"""WHAT THE MODEL IS TOLD BEFORE IT HEARS ANYTHING."""

import re
from pathlib import Path

import mcps
from hands import apps

WORDS = Path(__file__).resolve().parent.parent / "prompt.md"

HEADING = re.compile(r"^## +([A-Z]+) *$", re.M)

COMMENT = re.compile(r"<!--.*?-->\s*", re.S)

# WHAT FOLLOWS THE STANDING RULES, IN THE ORDER IT IS SAID.
FINISHING_ORDER = ("CORE", "MESSAGING", "BROWSING", "REMEMBERING", "CONTACTS")


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

# THE LAST PROMPT COMPOSED, BESIDE THE TWO FACTS IT WAS COMPOSED OUT OF.
composed = None

out_of = None


def system_prompt():
    """THE STANDING PROMPT PLUS THE FACTS ONLY THIS MACHINE CAN SUPPLY."""
    global composed, out_of

    facts = (mcps.mention(), apps.listing())

    if composed is not None and facts == out_of:
        return composed

    remote, installed = facts
    parts = [STANDING, FINISHING]

    if remote:
        parts.append(remote)

    if installed:
        parts.append(f"{MACHINE}\n\n{installed}")

    composed = "\n\n".join(parts)
    out_of = facts

    return composed
