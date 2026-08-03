"""EVERYTHING HAPPY CAN DO. ONE FOLDER PER PART OF THE MACHINE.

A MODULE HERE IS A NAMESPACE, NOT A MIND OF ITS OWN. IT EXPORTS TOOLS AND THE
ONE GRAPH IN brain/ CALLS THEM DIRECTLY, BECAUSE EVERY EXTRA HOP THROUGH THE
MODEL IS ANOTHER SECOND OF SILENCE BEFORE HAPPY SPEAKS.

TO ADD A CAPABILITY: WRITE THE FOLDER, GIVE IT A TOOLS LIST, ADD IT TO MODULES.
"""

import eyes
import mcps
from hands import apps, asking, browser, coder, controls, desktop, files, shell

# THE ORDER THE MODEL SEES THEM IN: NARROW AND SAFE FIRST, SO THEY READ AS THE
# OBVIOUS CHOICE BEFORE THE SHELL AND THE SCREEN DO.
MODULES = [apps, controls, files, mcps, eyes, desktop, browser, coder, shell]


def tools():
    """EVERY TOOL FROM EVERY MODULE, FLAT, READY TO BIND TO A MODEL.

    A MODULE WITH NOTHING IN IT YET REGISTERS NOTHING, WHICH IS HOW A CAPABILITY
    BEING REBUILT STAYS IN THE LIST WITHOUT BREAKING THE START UP.
    """
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
