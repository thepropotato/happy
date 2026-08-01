"""SERVICES HAPPY CAN REACH THAT DO NOT RUN ON THIS MACHINE.

EVERYTHING ELSE UNDER hands/ IS PYTHON SITTING BESIDE THE MODEL. THESE ARE NOT:
THEY ARE MCP SERVERS OVER HTTP OR A PIPE, WHICH IS WHY THIS FOLDER IS NAMED FOR
WHAT THEY LITERALLY ARE RATHER THAN FOR A PART OF A PERSON.

NOTHING IS CONNECTED UNTIL SOMEBODY CONNECTS IT, SO A PERSON WHO NEVER OPENS THE
PANEL HAS EXACTLY THE TOOLS THIS COMPUTER ALWAYS HAD.
"""

from langchain_core.tools import tool
from mcp.types import Tool

from mcps import binding, pool, store
from mcps.joining import (
    add,
    connect,
    custom,
    disconnect,
    enable,
    forget,
    fresh,
    paste,
    stir,
)
from mcps.whatsapp import qr
from memory import settings

TOOLS = []

NOTHING = "Nothing is connected."

MENTION = (
    "Some of your tools reach services on the internet rather than this computer. "
    "They are named after the service they belong to, like notion_search. They are "
    "slower than the ones on this machine, so when either would do, use the local one."
)


def cap():
    return settings.get("mcps.cap", 6)


def offering():
    """EVERY TOOL FROM EVERY CONNECTED SERVICE, READY FOR THE GRAPH.

    BUILT OUT OF WHAT EACH SERVER SAID LAST TIME, NOT OUT OF ASKING IT NOW. THIS
    RUNS WHILE HAPPY IS STARTING AND MUST NEVER WAIT ON A NETWORK.
    """
    found = []
    taken = local_names()

    for row in store.every():
        if not row["enabled"] or not row["tools"]:
            continue

        built = binding.bind(
            row["label"],
            pool.session(row),
            remembered(row["tools"]),
            allowed=row["allowed"],
            cap=cap(),
            taken=taken,
        )

        taken.update(each.name for each in built)
        found.extend(built)

    return found + [connections] if found else found


def remembered(kept):
    """THE STORED TOOL LISTS BACK AS TOOLS. ONE THAT NO LONGER PARSES IS DROPPED."""
    found = []

    for each in kept:
        try:
            found.append(Tool(**each))
        except Exception:
            continue

    return found


def local_names():
    """WHAT THE TOOLS ON THIS MACHINE ARE CALLED, SO NOTHING REMOTE SHADOWS ONE.

    READ STRAIGHT OFF THE OTHER MODULES RATHER THAN THROUGH hands.tools(), WHICH
    WOULD COME BACK ROUND TO THIS FUNCTION AND NEVER STOP.
    """
    import hands

    return {each.name for module in hands.MODULES for each in getattr(module, "TOOLS", [])}


def mention():
    """THE LINE THE SYSTEM PROMPT GAINS, AND ONLY WHILE SOMETHING IS CONNECTED."""
    return MENTION if any(row["enabled"] for row in store.every()) else ""


@tool
def connections() -> str:
    """Say which outside services are connected right now, such as Notion or Linear.

    Use this when you are asked what you can reach, or when a service someone
    named does not seem to be there. It says nothing about this computer.
    """
    on = [row["label"] for row in store.every() if row["enabled"]]

    return ", ".join(on) if on else NOTHING


def drawn(behind=()):
    """THE WHOLE CONNECTIONS PANEL, FOR SOMETHING THAT HAS TO DRAW IT.

    behind IS THE CATALOGUE'S OWN HANDFUL OF SETTINGS. THEY COME BACK FOLDED AWAY
    AT THE BOTTOM RATHER THAN AT THE TOP, BECAUSE NOBODY OPENS THIS PANEL TO MOVE
    A TIMEOUT AND THREE SLIDERS IN FRONT OF THE SERVICES READ AS THE POINT OF IT.
    """
    from mcps import showing

    return showing.rows(behind)


def values():
    from mcps import showing

    return showing.values()


def start():
    """OPEN WHAT IS SWITCHED ON, IN THE BACKGROUND. SAFE TO CALL WHEN NONE ARE."""
    pool.warm()
