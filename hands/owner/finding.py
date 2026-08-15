"""THE NAME OF THE PERSON THIS COMPUTER BELONGS TO, OFF WHATEVER IS ALREADY SIGNED IN."""

import getpass
import os
import re
import sys

WINDOWS = "win32"

# THE FULL NAME WINDOWS KEEPS BESIDE AN ACCOUNT, NOT THE ONE IT IS LOGGED IN BY.
DISPLAY = 3

DIGITS = re.compile(r"^[\d\s+()-]+$")


def named():
    """THE BEST NAME ANYTHING HERE HAS FOR THEM, AND WHERE IT WAS READ."""
    for found, where in ((linked(), "their WhatsApp account"),
                         (account(), "the account on this computer"),
                         (login(), "the login name on this computer, so it may be short")):
        if found:
            return found, where

    return "", ""


def linked():
    """WHAT THEY CALL THEMSELVES ON THE WHATSAPP ACCOUNT THIS IS SIGNED IN AS."""
    try:
        from mcps.servers.whatsapp import talking

        found = talking.asked(talking.client().get_status()) or {}
    except Exception:
        return ""

    if not (found.get("connected") or found.get("authenticated")):
        return ""

    return clean(found.get("name"))


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
