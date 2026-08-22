"""THINGS THE PERSON HAS TAUGHT HAPPY TO DO THE SAME WAY EVERY TIME."""

import json
from datetime import datetime

from memory import storage

SAVE = """
INSERT INTO routines (name, description, steps, tools, examples, result, asked, at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(name) DO UPDATE SET
    description=excluded.description, steps=excluded.steps, tools=excluded.tools,
    examples=excluded.examples, result=excluded.result, asked=excluded.asked, at=excluded.at
"""

EVERYTHING = "SELECT * FROM routines ORDER BY runs DESC, at DESC"

RENAME = "UPDATE routines SET name = ?, at = ? WHERE name = ?"

DROP = "DELETE FROM routines WHERE name = ?"

RAN = "UPDATE routines SET runs = runs + 1 WHERE name = ?"

# THE FIRST LINE OF THE LISTING THE STANDING PROMPT GAINS.
SAYS = (
    "Saved routines. Each one is something this person has taught you to do the same way "
    "every time. Run one with run_routine the moment what they ask matches what it does, "
    "whether or not they say the word routine."
)

# A NAME NOBODY COULD SAY IS A NAME NOBODY COULD RUN.
LONGEST = 60

# A COUNTER THAT ONLY GOES UP, SO THE GRAPH KNOWS TO REBUILD ITS PROMPT.
turned = 0

# WHO ELSE WANTS TELLING WHEN ONE CHANGES.
told = None


def every():
    """EVERY ROUTINE, MOST USED FIRST."""
    return [unpack(row) for row in storage.read(EVERYTHING)]


def one(name):
    """THE ROUTINE BY THAT EXACT NAME, HOWEVER IT WAS SPELT OR SPACED."""
    wanted = plain(name)

    return next((each for each in every() if plain(each["name"]) == wanted), None)


def matched(said):
    """EVERY ROUTINE SOMEBODY COULD HAVE MEANT. ONE IS A RUN, MORE IS A QUESTION.

    A NAME IS RARELY SAID ON ITS OWN — "RUN MY MORNING BRIEF THING" IS STILL THE MORNING
    BRIEF — SO A NAME IS LOOKED FOR INSIDE THE WORDS TOO, BUT ONLY WHEN IT IS LONG ENOUGH
    THAT FINDING IT THERE MEANS ANYTHING."""
    wanted = plain(said)

    if not wanted:
        return []

    kept = every()
    exact = [each for each in kept if plain(each["name"]) == wanted]

    if exact:
        return exact

    return [each for each in kept if len(plain(each["name"])) > 3
            and (plain(each["name"]) in wanted or wanted in plain(each["name"]))]


def save(name, description="", steps="", tools=(), examples=(), result="", asked=""):
    """WRITE ONE DOWN, OVER WHATEVER WAS THERE UNDER THAT NAME."""
    called = tidy(name)

    if not called:
        return None

    storage.write(SAVE, (
        called,
        str(description or "").strip(),
        str(steps or "").strip(),
        json.dumps(sorted(set(tools or ()))),
        json.dumps(list(examples or ())),
        str(result or "").strip(),
        str(asked or "").strip(),
        now(),
    ))

    bump()

    return one(called)


def rename(name, to):
    """THE SAME ROUTINE UNDER A NEW NAME. None IF THERE WAS NOTHING TO RENAME."""
    found = one(name)
    called = tidy(to)

    if not found or not called:
        return None

    storage.write(RENAME, (called, now(), found["name"]))
    bump()

    return one(called)


def forget(name):
    found = one(name)

    if not found:
        return None

    storage.write(DROP, (found["name"],))
    bump()

    return found


def ran(name):
    """ONE MORE RUN AGAINST IT, SO THE LIST SORTS BY WHAT IS ACTUALLY USED."""
    try:
        storage.write(RAN, (name,))
    except Exception:
        pass


def listing():
    """THE LINES THE STANDING PROMPT GAINS, AND ONLY WHILE THERE IS ANYTHING TO SAY."""
    kept = every()

    if not kept:
        return ""

    lines = [f"- {each['name']} — {each['description'] or 'no description'}" for each in kept]

    return SAYS + "\n" + "\n".join(lines)


def version():
    return turned


def whenever(callback):
    """WHO TO TELL WHEN A ROUTINE IS SAVED, RENAMED OR FORGOTTEN.

    A ROUTINE IS MADE BY SAYING SO. THE PANEL WAS NEVER TOUCHED AND WOULD NEVER THINK TO
    ASK, SO IT IS TOLD INSTEAD — THE SAME DEAL A QR SCANNED IN A BROWSER TAB GETS."""
    global told

    told = callback


def bump():
    global turned

    turned += 1

    if told:
        try:
            told()
        except Exception:  # NOBODY IS KEPT FROM SAVING BY WHATEVER IS DRAWING.
            pass


def tidy(name):
    """A NAME AS IT WILL BE STORED: SAID THE WAY A PERSON SAYS IT, NOTHING MORE.

    A MODEL ASKED FOR A NAME REACHES FOR AN IDENTIFIER AND WRITES where_am_i, WHICH IS READ
    OUT AS THREE WORDS AND AN UNDERSCORE TWICE. WHAT JOINS WORDS ON A PAGE IS A SPACE."""
    said = " ".join(str(name or "").replace("_", " ").replace("-", " ").split())
    said = said.strip(" .,:;!?\"\'")

    return said[:LONGEST].lower()


def plain(said):
    """A NAME WITH THE SPACES, CAPITALS AND PUNCTUATION TAKEN OFF IT."""
    return "".join(each for each in str(said or "").lower() if each.isalnum())


def unpack(row):
    entry = dict(row)

    for key in ("tools", "examples"):
        try:
            entry[key] = json.loads(entry.get(key) or "[]")
        except ValueError:
            entry[key] = []

    return entry


def now():
    return datetime.now().astimezone().isoformat(timespec="milliseconds")
