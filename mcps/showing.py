"""THE CONNECTIONS PANEL AS A WHOLE: WHAT IS IN IT, AND IN WHAT ORDER.

THIS USED TO HAND BACK ORDINARY KNOBS, AND A LIST WHERE A TIMEOUT SLIDER, A
PASTED SECRET AND A THING YOU SIGN INTO ALL LOOKED IDENTICAL IS A LIST NOBODY CAN
READ. WHAT IS CONNECTED COMES FIRST NOW, WHAT IS NOT COMES NEXT, AND WHAT IS
RARELY TOUCHED IS FOLDED AWAY AT THE BOTTOM.
"""

from mcps import drawing, store, wording
from memory.knobs import folded, heading, text

ON = drawing.ON

NEW = "mcps.new"

ADDING = "mcps.adding"

BEHAVE = "mcps.behave"

CONNECTED = "Connected"

COLD = "Not connected"

REST = "Rest"

ADD = "Add a server of your own"

ADDRESS = "Address"

ADDRESSING = "A web address, or a command to run. Enter adds it."

EXAMPLE = "https://example.com/mcp"

BEHAVING = "How connections behave"


def rows(behind=()):
    """EVERY CONNECTION, CONNECTED ONES FIRST, AND THE RARELY TOUCHED AT THE END."""
    kept = {row["name"]: row for row in store.every()}
    live = []
    cold = []

    for known in drawing.listed():
        found = built(known, kept)
        (live if found["connected"] else cold).append(found)

    for name, row in list(kept.items()):  # WHATEVER SOMEBODY ADDED THEMSELVES.
        found = drawing.mine(name, row)
        (live if found["connected"] else cold).append(found)

    return sections(live, cold, behind)


def built(known, kept):
    if known.get("members"):
        return drawing.household(known, kept)

    return drawing.alone(known, kept.pop(known["name"], None))


def sections(live, cold, behind):
    drawn = []

    if live:
        drawn.append(heading(CONNECTED, tally(live)))
        drawn.extend(live)

    if cold:
        drawn.append(heading(COLD))
        drawn.extend(cold)

    drawn.append(heading(REST))
    drawn.append(folded(ADDING, ADD, "+", [text(NEW, ADDRESS, "", ADDRESSING, EXAMPLE)]))
    drawn.append(folded(BEHAVE, BEHAVING, "⚙", list(behind)))

    return drawn


def tally(live):
    """WHAT THE Connected HEADING SAYS ON ITS RIGHT: HOW MANY, AND HOW MUCH."""
    services = sum(each["signed"] for each in live)
    tools = sum(each["tools"] for each in live)

    return f"{services} · {wording.said(tools)}"


def values():
    """WHAT EACH GENERATED SWITCH IS SET TO. BUTTONS AND BOXES HOLD NOTHING."""
    return {ON + row["name"]: row["enabled"] for row in store.every()}
