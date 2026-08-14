"""EVERYTHING HAPPY CAN DO."""

import eyes
import mcps
from hands import apps, asking, browser, coder, controls, desktop, files, memory, shell, web

# EVERY MODULE, EVERY TURN.
MODULES = [apps, controls, files, memory, mcps, web, eyes, desktop, browser, coder, shell]


def tools():
    """EVERY TOOL FROM EVERY MODULE, FLAT, READY TO BIND TO A MODEL."""
    found = []

    for module in MODULES:
        found.extend(getattr(module, "TOOLS", []))

        # SOME TOOLS ONLY EXIST ONCE SOMETHING IS CONNECTED, SO NEVER CACHE THIS.
        offering = getattr(module, "offering", None)

        if offering:
            found.extend(offering())

    return asking.widened(found)


def names():
    return [each.name for each in tools()]
