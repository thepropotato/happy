"""FINDING A FILE FROM WHAT A PERSON CALLED IT."""

import os
import re
from datetime import datetime
from pathlib import Path

from hands.files import held

# SEARCHED IN THIS ORDER, NEAREST FIRST.
PLACES = ["Desktop", "Documents", "Downloads", "Pictures", "Movies", "Music"]

# NEVER WALKED. ENORMOUS, AND HOLDING NOTHING ANYONE ASKS FOR BY NAME.
AVOID = {
    "Library", "node_modules", ".git", ".venv", "venv", "__pycache__", ".Trash",
    "Applications", ".cache", ".npm", "site-packages", ".ollama", "Photos Library.photoslibrary",
}

MAX_DEPTH = 4
MAX_HITS = 12

DOWNLOADS = "Downloads"

# THE TIME BESIDE A NAME, AS THE REMINDERS SAY IT: A CLOCK FOR TODAY, A DATE FOR ANY OTHER DAY.
TODAY = "%H:%M"

OTHER = "%b"


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


def crawl(root, depth):
    """EVERY FOLDER UNDER root, WITHOUT DESCENDING INTO THE ENORMOUS."""
    for here, folders, names in os.walk(root):
        folders[:] = [f for f in folders if f not in AVOID and not f.startswith(".")]

        if len(Path(here).relative_to(root).parts) >= depth:
            folders[:] = []

        for name in folders:
            yield Path(here) / name


def dig(wanted, depth=MAX_DEPTH, limit=MAX_HITS):
    """FOLDERS WHOSE NAME ANSWERS TO wanted, NEAREST PLACES FIRST, NO REPEATS."""
    needle = str(wanted or "").lower().strip()
    asked = words(wanted)
    seen, hits = set(), []

    for root in roots():
        for path in crawl(root, depth):
            if matches(path.name.lower(), needle, asked) and path not in seen:
                seen.add(path)
                hits.append(path)

                if len(hits) >= limit:
                    return hits

    return hits


def words(wanted):
    """THE WORDS IN A NAME, HOWEVER IT WAS JOINED UP, WITHOUT THE EXTENSION.

    "offer_letter.pdf" AND "Offer Letter.pdf" ARE THE SAME REQUEST WRITTEN TWO WAYS, AND A
    PLAIN SUBSTRING SAYS THEY ARE NOT: THE MODEL ASKED FOR THE FIRST, THE SECOND WAS SITTING
    IN DOWNLOADS, AND THE ANSWER CAME BACK "nothing found" TWICE."""
    plain = str(wanted or "").lower().strip().strip('"').strip("'")
    plain = re.sub(r"\.[a-z0-9]{1,5}$", "", plain)

    return [each for each in re.split(r"[^a-z0-9]+", plain) if each]


def matches(name, needle, wanted):
    """WHETHER ONE FILE NAME ANSWERS TO wanted, AS WRITTEN OR WORD BY WORD."""
    if needle and needle in name:
        return True

    return bool(wanted) and all(each in name for each in wanted)


def hunt(wanted, depth=MAX_DEPTH, limit=MAX_HITS):
    """FILES WHOSE NAME ANSWERS TO wanted, NEAREST PLACES FIRST, NO REPEATS.

    THE WHOLE STRING IS TRIED FIRST SO AN EXACT ASK STILL RANKS THE WAY IT ALWAYS DID; THE
    WORDS ARE THE FALLBACK, WHICH IS WHAT LETS A NAME JOINED BY UNDERSCORES FIND ONE
    WRITTEN WITH SPACES."""
    needle = str(wanted or "").lower().strip()
    asked = words(wanted)
    seen, hits = set(), []

    for root in roots():
        for path in walk(root, depth):
            if matches(path.name.lower(), needle, asked) and path not in seen:
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


def folder(where):
    """THE FOLDER MEANT BY where, MADE IF NEED BE, AND DOWNLOADS WHEN NOBODY SAID."""
    said = (where or "").strip() or DOWNLOADS
    named = Path(said).expanduser()

    if named.is_dir():
        return named

    # A BARE NAME IS A FOLDER TO GO LOOKING FOR. A PATH IS A PLACE THEY SPELLED OUT, AND
    # GOING LOOKING FOR THAT IS HOW SOMETHING LANDS SOMEWHERE NOBODY ASKED FOR.
    if len(named.parts) == 1 and not named.is_absolute():
        named = home() / named

        if named.is_dir():
            return named

        hits = dig(said)
        exact = [each for each in hits if each.name.lower() == said.lower()]

        if hits:
            return (exact or hits)[0]

    named.mkdir(parents=True, exist_ok=True)

    return named


def changed(path):
    """WHEN THE THING WAS LAST WRITTEN, AS A UNIX TIME, OR 0 IF IT WILL NOT SAY."""
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def newest(paths):
    """THE THINGS, NEWEST FIRST. "THE MOST RECENT DOWNLOAD" IS ANSWERED FROM THE ORDER OF A
    LISTING, AND A LISTING IN ALPHABETICAL ORDER PUTS AN OLD FILE WHERE THE NEWEST ONE GOES."""
    return sorted(paths, key=changed, reverse=True)


def aged(path):
    """THE WHEN, SHORT ENOUGH TO SIT BESIDE THE NAME."""
    when = changed(path)

    if not when:
        return ""

    at = datetime.now().astimezone()
    when = datetime.fromtimestamp(when, at.tzinfo)

    if when.date() == at.date():
        return when.strftime(TODAY)

    return f"{when.day} {when.strftime(OTHER)}"

def describe(path):
    """A FILE WITH ITS SIZE AND WHEN IT LANDED, OR A FOLDER SAID TO BE ONE. A FOLDER GIVEN AS
    "0 KB" WAS ONCE READ AS AN EMPTY PROJECT, AND A WHOLE CODEBASE WAS WRITTEN OFF ON THE
    STRENGTH OF IT. THE TIME IS THERE BECAUSE WITHOUT IT NOTHING IN A LISTING SAYS WHICH OF
    THEM IS THE NEWEST, AND THE ANSWER GETS GUESSED FROM THE NAMES.

    EVERY PATH THE MODEL IS SHOWN IS REGISTERED HERE, WHICH IS WHAT LETS IT BE ACTED ON: THIS
    IS THE ONE PLACE EVERY LISTING TOOL PUTS A PATH IN FRONT OF IT."""
    held.offer(path)

    at = aged(path)
    when = f", {at}" if at else ""

    if path.is_dir():
        try:
            inside = sum(1 for each in path.iterdir() if not each.name.startswith("."))
        except OSError:
            inside = 0

        return f"{path}/ (a folder holding {inside} things{when})"

    size = path.stat().st_size

    if size < 1024**2:
        return f"{path} ({size / 1024:.0f} KB{when})"

    return f"{path} ({size / 1024**2:.1f} MB{when})"
