"""WHETHER A VIDEO IS ACTUALLY PLAYING, ASKED OF THE SYSTEM RATHER THAN THE SCREEN.

A STREAMING SITE BLANKS ITSELF IN EVERY SCREENSHOT, SO PIXELS CANNOT ANSWER THIS
AND A MOTION DETECTOR BUILT ON THEM SCORED WORSE THAN CHANCE. A PLAYER HOLDS A
WAKE LOCK THE WHOLE TIME IT PLAYS, THOUGH, AND THAT IS BOOKKEEPING NO DRM HIDES.
"""

import re
import subprocess

from eyes.attention import on_mac, on_windows

# HELD WHILE A VIDEO PLAYS AND DROPPED THE MOMENT IT PAUSES. "Playing audio" IS
# NOT THE SAME THING: A BROWSER KEEPS THAT ONE WHILE THE TAB MERELY EXISTS.
MAC_MARK = "Video Wake Lock"

MAC_LINE = re.compile(r"pid (\d+)\(([^)]*)\).*?named: \"" + MAC_MARK + "\"")

WINDOWS_MARK = "DISPLAY"

SECONDS = 4


def said(argv):
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=SECONDS)
    except (OSError, subprocess.SubprocessError):
        return None

    return done.stdout if done.returncode == 0 else None


def playing(pid=None):
    """True WHEN SOMETHING IS PLAYING, False WHEN NOTHING IS, None WHEN UNKNOWN."""
    if on_mac():
        return mac_playing(pid)

    if on_windows():
        return windows_playing()

    return None


def mac_playing(pid=None):
    out = said(["pmset", "-g", "assertions"])

    if out is None:
        return None

    holders = {int(found.group(1)) for found in MAC_LINE.finditer(out)}

    if not holders:
        return False

    return True if pid is None else pid in holders


def windows_playing():
    """powercfg NAMES WHAT IS HOLDING THE DISPLAY AWAKE, BUT ONLY FOR AN ADMIN."""
    out = said(["powercfg", "/requests"])

    if out is None:
        return None

    for block in out.split("\n\n"):
        if block.strip().startswith(WINDOWS_MARK) and "None." not in block:
            return True

    return False
