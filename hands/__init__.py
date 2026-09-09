"""EVERYTHING HAPPY CAN DO."""

import eyes
import mcps
from hands import (
    apps, browser, coder, controls, desktop, files, memory, owner, reasons, reminders, routines,
    shell, weather, web, wording,
)

# EVERY MODULE, EVERY TURN.
MODULES = [
    apps, controls, files, memory, owner, mcps, web, eyes, desktop, browser, coder, shell, wording,
    routines, reminders, weather,
]


def tools():
    """EVERY TOOL FROM EVERY MODULE, FLAT, READY TO BIND TO A MODEL."""
    found = []

    for module in MODULES:
        found.extend(getattr(module, "TOOLS", []))

        # SOME TOOLS ONLY EXIST ONCE SOMETHING IS CONNECTED, SO NEVER CACHE THIS.
        offering = getattr(module, "offering", None)

        if offering:
            found.extend(offering())

    return reasons.widened(found)


def names():
    return [each.name for each in tools()]