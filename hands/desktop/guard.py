"""WHAT A CLICK WOULD COST IF IT WERE THE WRONG ONE.

THE SAME SHAPE AS THE SHELL'S GUARD, APPLIED TO WHAT IS WRITTEN ON THE THING
BEING PRESSED. A MISHEARD WORD IS A DIFFERENT BUTTON, AND SOME BUTTONS DO NOT
HAVE AN UNDO. THIS CATCHES A CARELESS MODEL, NOT A HOSTILE ONE.
"""

import re

RISKY = [
    (r"\b(delete|erase|trash|discard|remove|destroy)\b", "deletes something"),
    (r"\b(send|post|publish|reply all|share)\b", "sends something to someone"),
    (r"\b(buy|pay|purchase|order|checkout|subscribe|donate)\b", "spends money"),
    (r"\b(install|uninstall|update now|upgrade)\b", "installs or removes software"),
    (r"\b(allow|grant|trust|always allow|accept)\b", "grants a permission"),
    (r"\b(quit|shut ?down|restart|log ?out|sign ?out)\b", "closes things down"),
    (r"\b(format|reset|factory|wipe)\b", "resets something"),
    (r"\b(deactivate|close account|unsubscribe|cancel subscription)\b", "cannot be undone"),
    (r"\b(don't save|do not save)\b", "throws away unsaved work"),
]

# SHORTCUTS THAT END SOMETHING RATHER THAN CHANGE IT.
RISKY_KEYS = [
    (r"\bcmd\+q\b", "quits the application"),
    (r"\bcmd\+shift\+q\b", "logs out"),
    (r"\balt\+f4\b", "closes the window"),
    (r"\bcmd\+delete\b", "deletes something"),
    (r"\bctrl\+alt\+delete\b", "interrupts the whole machine"),
]

CHECKS = [(re.compile(pattern, re.IGNORECASE), reason) for pattern, reason in RISKY]
KEY_CHECKS = [(re.compile(pattern, re.IGNORECASE), reason) for pattern, reason in RISKY_KEYS]


def danger(label):
    """WHY PRESSING THIS NEEDS ASKING ABOUT, OR None WHEN IT DOES NOT."""
    for check, reason in CHECKS:
        if check.search(label or ""):
            return reason

    return None


def danger_keys(keys):
    """WHY THIS SHORTCUT NEEDS ASKING ABOUT, OR None WHEN IT DOES NOT."""
    tidy = str(keys or "").replace(" ", "").lower()

    for check, reason in KEY_CHECKS:
        if check.search(tidy):
            return reason

    return None
