"""EVERY SAVED ROUTINE AS ONE ROW, FOR SOMEBODY WHO WOULD RATHER LOOK THAN ASK."""

from memory import routines
from memory.kinds import action, folded, state

FORGET = "forget"

NONE = "routines.none"

EMPTY = "Nothing saved yet"

NOTHING = (
    'Say "save that as a routine" after Happy has done something and it will be here, '
    "under a name he gives it."
)

# WHAT IS SHOWN OF THE TOOLS BEFORE THE ROW WOULD BE LONGER THAN IT IS USEFUL.
MOST = 6


def rows():
    """EVERY ROUTINE, MOST USED FIRST, AND ONE LINE WHERE THERE ARE NONE."""
    kept = routines.every()

    if not kept:
        return [state(NONE, EMPTY, "", NOTHING)]

    return [one(each) for each in kept]


def one(found):
    """A ROW THAT OPENS INTO WHAT THE ROUTINE ACTUALLY IS, AND A WAY TO BE RID OF IT."""
    return folded(
        f"routines.{found['name']}",
        found["name"],
        marked(found),
        inside(found),
    )


def inside(found):
    """WHAT THE ROW SAYS ONCE IT IS OPEN: WHAT IT DOES, ITS STEPS, AND WHAT IT ENDS ON."""
    key = f"routines.{found['name']}"
    said = [
        ("does", "What it does", found["description"], None),
        ("steps", "Steps", counted(found), found["steps"] or None),
        ("tools", "Tools", listed(found["tools"]), None),
        ("ends", "Ends with", found["result"], None),
        ("asked", "Saved from", found["asked"], None),
    ]

    shown = [state(f"{key}.{name}", label, says, hint) for name, label, says, hint in said if says]

    return shown + [action(key, "Forget it", FORGET, "Forget", "Gone for good.")]


def marked(found):
    """THE COUNT BESIDE THE NAME, WHICH IS THE ONE THING WORTH SEEING WITHOUT OPENING IT."""
    runs = found["runs"]

    return "" if not runs else f"{runs}"


def counted(found):
    steps = len([each for each in (found["steps"] or "").splitlines() if each.strip()])

    return "" if not steps else f"{steps} {'step' if steps == 1 else 'steps'}"


def listed(tools):
    """THE TOOLS IT IS BOUND TO, WHICH IS WHAT MAKES IT RELIABLE AND SO IS WORTH SHOWING."""
    if not tools:
        return "Anything — this one was saved without a run behind it"

    shown = ", ".join(tools[:MOST])

    return shown if len(tools) <= MOST else f"{shown} and {len(tools) - MOST} more"


def forget(name):
    """WHAT THE FORGET BUTTON ASKS FOR. THE KEY IT SENDS CARRIES THE NAME."""
    called = str(name or "")

    return routines.forget(called[len("routines."):] if called.startswith("routines.") else called)
