"""EVERYTHING HAPPY CAN DO. ONE FOLDER PER PART OF THE MACHINE.

A MODULE HERE IS A NAMESPACE, NOT A MIND OF ITS OWN. IT EXPORTS TOOLS AND THE
ONE GRAPH IN brain/ CALLS THEM DIRECTLY, BECAUSE EVERY EXTRA HOP THROUGH THE
MODEL IS ANOTHER SECOND OF SILENCE BEFORE HAPPY SPEAKS.

TO ADD A CAPABILITY: WRITE THE FOLDER, GIVE IT A TOOLS LIST, ADD IT TO MODULES.
"""

import eyes
import mcps
from hands import apps, asking, browser, coder, controls, desktop, files, memory, shell, web

# ALWAYS BOUND — THESE ARE CHEAP, BROADLY USED, AND SAFE.
CORE_MODULES = [apps, controls, files, memory, eyes, desktop]

# BOUND ONLY WHEN THE INTENT PROFILE SAYS SO.
CONDITIONAL = {
    "messaging": [mcps],
    "contacts": [mcps],
    "browsing": [web, browser],
    "coding": [coder, shell],
}

# FULL SET — USED WHEN NO PROFILE IS GIVEN (BACKWARD COMPATIBLE DEFAULT).
MODULES = [apps, controls, files, memory, mcps, web, eyes, desktop, browser, coder, shell]


def tools(profile=None):
    """EVERY TOOL FROM EVERY MODULE, FLAT, READY TO BIND TO A MODEL.

    profile IS A frozenset OF INTENT LABELS. None MEANS ALL TOOLS.
    A MODULE WITH NOTHING IN IT YET REGISTERS NOTHING, WHICH IS HOW A CAPABILITY
    BEING REBUILT STAYS IN THE LIST WITHOUT BREAKING THE START UP.
    """
    if profile is None:
        active = MODULES
    else:
        seen = set()
        active = []

        for mod in CORE_MODULES:
            if id(mod) not in seen:
                seen.add(id(mod))
                active.append(mod)

        for label, mods in CONDITIONAL.items():
            if label in profile:
                for mod in mods:
                    if id(mod) not in seen:
                        seen.add(id(mod))
                        active.append(mod)

    found = []

    for module in active:
        found.extend(getattr(module, "TOOLS", []))

        # SOME TOOLS ONLY EXIST ONCE SOMETHING IS CONNECTED, SO NEVER CACHE THIS.
        offering = getattr(module, "offering", None)

        if offering:
            found.extend(offering())

    return asking.widened(found)


def names():
    return [each.name for each in tools()]