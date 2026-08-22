"""WHICH ROUTINE SOMEBODY MEANT, AND THE WORDS FOR WHEN IT IS NOT ONE."""

import re

from hands import reasons
from memory import conversation, routines

# WHAT SITS IN FRONT OF A NAME WITHOUT BEING PART OF IT.
BEFORE = frozenset((
    "happy", "hey", "ok", "okay", "please", "can", "could", "would", "will", "you", "just",
    "now", "go", "run", "do", "start", "execute", "perform", "launch", "my", "the", "a",
))

# AND WHAT TRAILS OFF THE END OF ONE.
AFTER = frozenset(("please", "now", "routine", "thing", "one", "again", "for", "me"))

WORDS = re.compile(r"[a-z0-9']+")

# HOW A STEP NAMES THE TOOL IT MUST USE, WHICH IS THE ONE THING TYING PROSE TO A REAL CALL.
REFERENCE = re.compile(r"[ \t]*\$\{TOOL:\s*([A-Za-z0-9_.-]+)\s*\}")

# PAST THIS IT IS A SENTENCE ABOUT SOMETHING, NOT SOMEBODY SAYING A NAME.
MOST = 8

# HOW MANY NAMES ARE WORTH READING OUT WHEN SOMEBODY ASKS FOR ONE THAT IS NOT THERE.
FEW = 5

NONE = "There are no saved routines yet."

TAKEN = (
    'There is already a routine called "{name}". Tell me another name for this one, or say '
    "to replace the one that is there."
)


def only(name):
    """THE ONE ROUTINE MEANT, OR THE WORDS SAYING WHY THERE IS NOT ONE.

    A NAME THAT MATCHES SEVERAL IS READ BACK RATHER THAN GUESSED AT, BECAUSE RUNNING THE
    WRONG ROUTINE IS A THING DONE THAT NOBODY ASKED FOR."""
    found = routines.matched(name)

    if not found:
        return None, reasons.no(f'I have not got a routine called "{name}". {otherwise()}')

    if len(found) > 1:
        return None, reasons.no(f"That could be {listed(found)}. Which one?")

    return found[0], None


def grounded(steps):
    """A STEP LIST'S ${TOOL: x} POINTERS CHECKED AGAINST THE TOOLS THERE ACTUALLY ARE.

    ONE POINTING AT SOMETHING THAT IS NOT THERE IS A ROUTINE THAT WILL FAIL LATER AND
    QUIETLY, SO THE POINTER COMES OUT NOW AND THE STEP KEEPS ITS WORDS. WHAT IS REAL JOINS
    THE TOOLS THE ROUTINE IS BOUND TO, WHICH IS WHAT MAKES A STEP BIND WHAT IT NAMES."""
    import hands

    here = set(hands.names())
    found = set()

    def check(mark):
        if mark.group(1) not in here:
            return ""

        found.add(mark.group(1))

        return mark.group(0)

    return REFERENCE.sub(check, steps or "").strip(), sorted(found)


def spoken(said):
    """THE ROUTINE SOMEBODY PLAINLY ASKED TO RUN, OR NOTHING AT ALL.

    "RUN MY MORNING BRIEF" HAS TO GO AND RUN THE MORNING BRIEF, EVERY TIME, AND NOT MOSTLY.
    LEFT TO THE MODEL IT READS THE LINE SAYING WHAT THE ROUTINE DOES, DECIDES IT KNOWS HOW
    TO DO THAT, AND DOES IT ITSELF — WHICH IS THE ONE THING A SAVED ROUTINE EXISTS TO STOP.
    SO THE PLAIN FORM IS MATCHED HERE INSTEAD, WHERE IT CANNOT BE TALKED OUT OF. ANYTHING
    LESS PLAIN THAN A RUN WORD AND A NAME IS LEFT TO THE MODEL, WHICH IS WHERE JUDGEMENT
    BELONGS."""
    words = WORDS.findall(str(said or "").lower())

    if not words or len(words) > MOST:
        return None

    kept = {routines.plain(each["name"]): each for each in routines.every()}

    if not kept:
        return None

    # THE WHOLE THING FIRST AND THE TRIMMINGS AFTER, SO A ROUTINE ACTUALLY CALLED "THE DAY
    # AHEAD" IS FOUND BEFORE "THE" IS TAKEN OFF THE FRONT OF IT.
    for start in edges(words, BEFORE):
        for end in edges(reversed(words), AFTER, len(words)):
            found = kept.get(routines.plain("".join(words[start:end]))) if end > start else None

            if found:
                return found

    return None


def edges(words, filler, backwards=None):
    """WHERE A NAME COULD START, OR END, ONCE THE FILLER IS TAKEN OFF A WORD AT A TIME."""
    found = [backwards if backwards is not None else 0]

    for word in words:
        if word not in filler:
            break

        found.append(found[-1] - 1 if backwards is not None else found[-1] + 1)

    return found


def listed(found):
    return " or ".join(f'"{each["name"]}"' for each in found[:FEW])


def otherwise():
    """WHAT THERE IS INSTEAD, SO A NO IS NEVER ONLY A NO."""
    kept = routines.every()

    if not kept:
        return NONE

    return f"There is {', '.join(chr(34) + each['name'] + chr(34) for each in kept[:FEW])}."


def captured(found):
    """WHAT A SAVE ACTUALLY TOOK, SAID BACK SO A HALF A JOB CAN BE SPOTTED WHILE IT IS STILL
    THE THING BEING TALKED ABOUT, AND NOT A WEEK LATER WHEN IT WILL NOT RUN."""
    said = counted(found)
    from_ = f' Taken from what you said: "{found["asked"]}".' if found.get("asked") else ""

    return f"{said}{from_}"


def described(found):
    said = found["description"] or "no description"

    return f'"{found["name"]}" — {said}. {counted(found)} Run {times(found["runs"])}.'


def counted(found):
    steps = len([each for each in (found["steps"] or "").splitlines() if each.strip()])
    tools = len(found["tools"])

    if not steps:
        return "No steps in it."

    said = f"{steps} {'step' if steps == 1 else 'steps'}"

    return f"{said}, {tools} {'tool' if tools == 1 else 'tools'}." if tools else f"{said}, no tools."


def times(runs):
    return "never" if not runs else "once" if runs == 1 else f"{runs} times"


def asked():
    """THE PERSON'S OWN WORDS THIS TURN, WHICH ARE WHAT THE ROUTINE IS ACTUALLY RUN ON.

    TAKEN OFF THE EXCHANGE RATHER THAN OUT OF A TOOL ARGUMENT, BECAUSE A ROUTINE THAT SAYS
    "SEND IT TO $who" NEEDS THE SENTENCE THEY SAID AND NOT A TIDIED UP VERSION OF IT."""
    row = conversation.here.get()

    if row is None:
        return ""

    found = [each for each in conversation.history(1) if each.get("id") == row]

    return (found[0].get("message") or "") if found else ""
