"""FINDING A FILE FROM WHAT A PERSON CALLED IT."""

import os
from pathlib import Path

# SEARCHED IN THIS ORDER, NEAREST FIRST.
PLACES = ["Desktop", "Documents", "Downloads", "Pictures", "Movies", "Music"]

# NEVER WALKED. ENORMOUS, AND HOLDING NOTHING ANYONE ASKS FOR BY NAME.
AVOID = {
    "Library", "node_modules", ".git", ".venv", "venv", "__pycache__", ".Trash",
    "Applications", ".cache", ".npm", "site-packages", ".ollama", "Photos Library.photoslibrary",
}

MAX_DEPTH = 4
MAX_HITS = 12


def home():
    return Path.home()


def roots():
    """WHERE TO LOOK, NEAREST FIRST, SKIPPING THE ONES THAT DO NOT EXIST."""
    found = [home() / place for place in PLACES]

    return [path for path in found if path.is_dir()] + [home()]


def walk(root, depth):
    """EVERY FILE UNDER root, WITHOUT DESCENDING INTO THE ENORMOUS."""
    for here, folders, names in os.walk(root):
        folders[:] = [f for f in folders if f not in AVOID and not f.startswith(".")]

        if len(Path(here).relative_to(root).parts) >= depth:
            folders[:] = []

        for name in names:
            if not name.startswith("."):
                yield Path(here) / name


def hunt(wanted, depth=MAX_DEPTH, limit=MAX_HITS):
    """FILES WHOSE NAME CONTAINS wanted, NEAREST PLACES FIRST, NO REPEATS."""
    needle = wanted.lower().strip()
    seen, hits = set(), []

    for root in roots():
        for path in walk(root, depth):
            if needle in path.name.lower() and path not in seen:
                seen.add(path)
                hits.append(path)

                if len(hits) >= limit:
                    return hits

    return hits


def locate(where):
    """THE PATH MEANT BY where, WHETHER IT IS A PATH OR A DESCRIPTION."""
    direct = Path(where).expanduser()

    if direct.exists():
        return direct, None

    hits = hunt(where)

    if not hits:
        return None, f"Nothing found called {where}."

    if len(hits) > 1 and hits[0].name.lower() != where.lower():
        listing = ", ".join(str(p) for p in hits[:5])

        return hits[0], f"Several matched, reading the first. Others: {listing}"

    return hits[0], None


def describe(path):
    size = path.stat().st_size

    if size < 1024**2:
        return f"{path} ({size / 1024:.0f} KB)"

    return f"{path} ({size / 1024**2:.1f} MB)"
