"""THROWING THE OLD AWAY. NOTHING GOES UNLESS A SETTING SAYS HOW LONG TO KEEP IT."""

import time
from pathlib import Path

from memory import settings, storage

OLDER = "DELETE FROM messages WHERE epoch < ?"

DAY = 86400

SUFFIX = ".wav"


def prune(recordings=None):
    """WHAT WAS THROWN AWAY, AS A SENTENCE, OR None IF NOTHING WAS."""
    gone = [messages(), wavs(recordings)]
    said = [line for line in gone if line]

    return ", ".join(said) if said else None


def messages():
    kept = settings.get("memory.messages")

    if not kept:
        return None

    try:
        with storage.connect() as handle:
            count = handle.execute(OLDER, (cutoff(kept),)).rowcount
    except Exception:  # A TIDY UP IS NEVER WORTH A FAILED START.
        return None

    return f"{count} messages" if count > 0 else None


def wavs(folder):
    kept = settings.get("memory.recordings")

    if not kept or not folder:
        return None

    folder = Path(folder)

    if not folder.is_dir():
        return None

    old = cutoff(kept)
    count = 0

    for path in folder.glob(f"*{SUFFIX}"):
        try:
            if path.stat().st_mtime < old:
                path.unlink()
                count += 1
        except OSError:
            continue

    return f"{count} recordings" if count > 0 else None


def cutoff(days):
    return time.time() - days * DAY
