"""WHERE IN THE WORLD THIS COMPUTER IS, AND WHAT THE TIME IS ON IT."""

import ctypes
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

MACOS = "darwin"
WINDOWS = "win32"

ZONEINFO = "zoneinfo"

LOCALTIME = Path("/etc/localtime")

# THE LOCALE AS THE SYSTEM WRITES IT, WHICH IS WHERE THE COUNTRY COMES FROM.
APPLE_LOCALE = ["defaults", "read", "-g", "AppleLocale"]

WINDOWS_ZONE = ["tzutil", "/g"]

NAME_LENGTH = 85  # WHAT GetUserDefaultLocaleName WANTS, IN CHARACTERS.

QUIET = {"capture_output": True, "text": True, "timeout": 4}


def report():
    """THE PLACE AND THE MOMENT, IN A FEW LINES."""
    now = datetime.now().astimezone()
    place = country()

    return "\n".join(
        [
            f"Country: {place or 'unknown'}",
            f"Time zone: {zone() or now.tzname() or 'unknown'}",
            f"Local time: {now.strftime('%A %d %B %Y, %H:%M')} ({now.strftime('%z')})",
            f"Language: {tongue() or 'unknown'}",
        ]
    )


def locale():
    """THE SYSTEM'S OWN LOCALE, LIKE en_IN OR en-GB."""
    if sys.platform == MACOS:
        found = asked(APPLE_LOCALE)

        if found:
            return found

    if sys.platform == WINDOWS:
        found = windows_locale()

        if found:
            return found

    for name in ("LC_ALL", "LC_CTYPE", "LANG", "LANGUAGE"):
        found = os.environ.get(name, "").split(".")[0].split(":")[0]

        if found and found not in ("C", "POSIX"):
            return found

    return ""


def country():
    """THE TWO LETTERS AFTER THE LANGUAGE, WHICH IS THE COUNTRY IT IS SET TO."""
    parts = locale().replace("-", "_").split("_")

    for part in parts[1:]:
        if len(part) == 2 and part.isalpha():
            return part.upper()

    return ""


def tongue():
    return locale().replace("-", "_").split("_")[0]


def zone():
    """THE ZONE BY NAME, LIKE Asia/Kolkata, WHICH SAYS THE PLACE AND NOT JUST THE OFFSET."""
    if sys.platform == WINDOWS:
        return asked(WINDOWS_ZONE)

    try:
        whole = LOCALTIME.resolve()
    except OSError:
        return ""

    parts = whole.parts

    if ZONEINFO not in parts:
        return ""

    return "/".join(parts[parts.index(ZONEINFO) + 1 :])


def windows_locale():
    buffer = ctypes.create_unicode_buffer(NAME_LENGTH)

    try:
        if ctypes.windll.kernel32.GetUserDefaultLocaleName(buffer, NAME_LENGTH):
            return buffer.value
    except (AttributeError, OSError):
        return ""

    return ""


def asked(command):
    try:
        done = subprocess.run(command, **QUIET)
    except (OSError, subprocess.SubprocessError):
        return ""

    return done.stdout.strip() if done.returncode == 0 else ""
