"""WHAT IS INSTALLED, BY THE NAME A PERSON WOULD SAY."""

import os
import sys
from pathlib import Path

from tongue.names import resolve as match

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
    """THE INSTALLED NAME CLOSEST TO WHAT WAS SAID, AND WHETHER IT IS CLOSE ENOUGH TO OPEN
    WITHOUT ASKING."""
    return match(spoken, apps())
