"""THE NAME OF THE PERSON THIS COMPUTER BELONGS TO, OFF WHATEVER THEY ARE SIGNED IN TO."""

import getpass
import os
import re
import sys

from hands.owner import asking
from mcps import registry

WINDOWS = "win32"

# THE FULL NAME WINDOWS KEEPS BESIDE AN ACCOUNT, NOT THE ONE IT IS LOGGED IN BY.
DISPLAY = 3

HERE = "the account on this computer"

LOGIN = "the login name on this computer, so it may be short"

DIGITS = re.compile(r"^[\d\s+()-]+$")


def named():
    """THE BEST NAME ANYTHING HAS FOR THEM, WHERE IT CAME FROM, AND WHAT ELSE CALLS THEM WHAT.

    THE SERVICES GO FIRST BECAUSE EACH ONE IS AN ACCOUNT THEY SIGNED INTO AND NAMED
    THEMSELVES. THIS COMPUTER IS ASKED TOO, AND ANSWERS EVEN WITH NOTHING CONNECTED AT ALL."""
    services = whittled((said, registry.label(name)) for said, name in asking.named())
    found = services + whittled([(account(), HERE), (login(), LOGIN)], services)

    if not found:
        return "", "", []

    best = fullest(found)

    # ONLY THE SERVICES: THIS COMPUTER'S OWN TWO ARE THE SAME NAME TWICE, ONCE BADLY, AND
    # READING THEM BACK AS SOMEWHERE ELSE HE IS KNOWN WOULD BE A LIE ABOUT BOTH.
    others = [each for each in services if each[0].lower() != best[0].lower()]

    return best[0], best[1], others


def whittled(found, already=()):
    """WHAT IS ACTUALLY A NAME, EACH ONE ONCE."""
    kept = []
    seen = {said.lower() for said, _ in already}

    for said, where in found:
        said = clean(said)

        if not said or said.lower() in seen:
            continue

        seen.add(said.lower())
        kept.append((said, where))

    return kept


def fullest(found):
    """A NAME WITH A SURNAME ON IT IS THE ONE THEY GO BY, WHICHEVER SERVICE HELD IT."""
    for each in found:
        if " " in each[0]:
            return each

    return found[0]


def account():
    """THE FULL NAME ON THIS MACHINE'S OWN ACCOUNT, WHICH PEOPLE FILL IN HONESTLY."""
    if sys.platform == WINDOWS:
        return windows()

    try:
        import pwd

        return clean(pwd.getpwuid(os.getuid()).pw_gecos.split(",")[0])
    except Exception:
        return ""


def windows():
    try:
        import ctypes

        size = ctypes.c_ulong(0)
        ctypes.windll.secur32.GetUserNameExW(DISPLAY, None, ctypes.byref(size))

        held = ctypes.create_unicode_buffer(size.value)

        if ctypes.windll.secur32.GetUserNameExW(DISPLAY, held, ctypes.byref(size)):
            return clean(held.value)
    except Exception:
        pass

    return ""


def login():
    try:
        return clean(getpass.getuser())
    except Exception:
        return ""


def clean(value):
    """A NUMBER IS WHAT THESE HOLD WHEN NOBODY EVER TYPED A NAME, AND IT IS NOT ONE."""
    said = str(value or "").strip()

    return "" if DIGITS.match(said) else said
