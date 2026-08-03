"""WHAT IS INSTALLED, BY THE NAME A PERSON WOULD SAY.

A DIRECTORY SCAN AND NOT A QUESTION PUT TO ANYTHING. BOTH SYSTEMS KEEP A FOLDER
MEANT FOR A PERSON TO BROWSE, AND EVERY ENTRY IN IT IS ALREADY NAMED THE WAY A
PERSON WOULD SAY IT. system_profiler AND THE REGISTRY ARE SLOW ENOUGH TO NOTICE.
"""

import difflib
import os
import sys
from pathlib import Path

MACOS = "darwin"
WINDOWS = "win32"  # ALSO ON 64 BIT. THE NAME NEVER CHANGED.

MAC_FOLDERS = [
    Path("/Applications"),
    Path("/System/Applications"),
    Path.home() / "Applications",
]

# APPS SIT ONE FOLDER DEEP TOO, LIKE /System/Applications/Utilities.
MAC_PATTERNS = ["*.app", "*/*.app"]

MENU = Path("Microsoft/Windows/Start Menu/Programs")

# TWO START MENUS, ONE FOR EVERYONE AND ONE FOR YOU. WINDOWS SHOWS THEM MERGED.
WINDOWS_ROOTS = ["PROGRAMDATA", "APPDATA"]
WINDOWS_PATTERNS = ["**/*.lnk"]

# WHAT INSTALLERS LEAVE BESIDE THE APP. WHOLE WORD, SO A REAL APP SURVIVES.
SKIP = {"uninstall", "readme", "documentation"}

SENTENCE = "Apps installed on this computer: "

# SPEECH ARRIVES MISHEARD MORE OFTEN THAN WRONG, SO THIS IS FORGIVING ON PURPOSE.
MATCH_CUTOFF = 0.6

# "slack" AND "clock" SCORE 0.6 AGAINST EACH OTHER, "photoshop" AND "Photos" 0.8.
SURE_CUTOFF = 0.85


def apps():
    """EVERY APP BY THE NAME A PERSON WOULD SAY, SORTED, NO REPEATS."""
    names = set()

    for folder in folders():
        for pattern in patterns():
            names.update(path.stem for path in folder.glob(pattern))

    return sorted((name for name in names if keep(name)), key=str.lower)


def listing():
    """THE SAME LIST AS ONE LINE TO HAND A MODEL. EMPTY WHEN NOTHING IS FOUND."""
    installed = apps()

    return SENTENCE + ", ".join(installed) + "." if installed else ""


def folders():
    """WHERE TO LOOK. EMPTY ON A PLATFORM WE DO NOT KNOW."""
    if sys.platform == MACOS:
        return MAC_FOLDERS

    if sys.platform == WINDOWS:
        roots = [os.environ.get(name) for name in WINDOWS_ROOTS]

        return [Path(root) / MENU for root in roots if root]

    return []


def patterns():
    return MAC_PATTERNS if sys.platform == MACOS else WINDOWS_PATTERNS


def keep(name):
    return not SKIP.intersection(name.lower().split())


def resolve(spoken):
    """THE INSTALLED NAME CLOSEST TO WHAT WAS SAID, AND WHETHER IT IS CLOSE
    ENOUGH TO OPEN WITHOUT ASKING. (None, False) WHEN NOTHING IS NEAR."""
    lowered = {name.lower(): name for name in apps()}
    said = spoken.lower().strip()

    if said in lowered:
        return lowered[said], True

    shortened = [name for low, name in lowered.items() if shortens(said, low)]

    if len(shortened) == 1:
        return shortened[0], True

    close = difflib.get_close_matches(said, lowered, n=1, cutoff=MATCH_CUTOFF)

    if not close:
        return (shortened[0], False) if shortened else (None, False)

    ratio = difflib.SequenceMatcher(None, said, close[0]).ratio()

    return lowered[close[0]], ratio >= SURE_CUTOFF and not shortened


def shortens(said, name):
    """WHETHER A NAME SAID SHORT IS STILL THIS NAME. IT HAS TO START A WORD OF
    IT: "chrome" IS Google Chrome, WHILE "word" IS NOT Passwords."""
    at = name.find(said)

    return at == 0 or (at > 0 and name[at - 1] == " ")
