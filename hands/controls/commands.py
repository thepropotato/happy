"""RUNNING THE SMALL COMMANDS THE SETTINGS LIVE BEHIND.

EVERY CONTROL IN THIS FOLDER IS WRITTEN FOR BOTH SYSTEMS SIDE BY SIDE, SO A
FEATURE THAT WORKS ON ONLY ONE OF THEM IS VISIBLE RATHER THAN HIDDEN.
"""

import re
import subprocess
import sys

MACOS = "darwin"
WINDOWS = "win32"

TIMEOUT_SECONDS = 15

UNSUPPORTED = "That is not something I can change on this computer."
REFUSED = "The system would not do that."


def on_mac():
    return sys.platform == MACOS


def on_windows():
    return sys.platform == WINDOWS


def run(argv, timeout=TIMEOUT_SECONDS, feed=None):
    """WHAT IT PRINTED, OR None WHEN IT REFUSED."""
    try:
        done = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout, input=feed
        )
    except (OSError, subprocess.SubprocessError):
        return None

    return done.stdout.strip() if done.returncode == 0 else None


def osascript(text):
    return run(["osascript", "-e", text])


def powershell(text):
    return run(["powershell", "-NoProfile", "-NonInteractive", "-Command", text])


def number(said, default=None):
    """THE FIRST NUMBER IN SOME OUTPUT, OR default."""
    found = re.search(r"-?\d+(?:\.\d+)?", said or "")

    if not found:
        return default

    value = float(found.group())

    return int(value) if value.is_integer() else value


def clamp(level, low=0, high=100):
    """A LEVEL A PERSON ASKED FOR, KEPT INSIDE THE RANGE, OR None IF IT IS NOT
    A NUMBER AT ALL."""
    try:
        return max(low, min(high, int(level)))
    except (TypeError, ValueError):
        return None
