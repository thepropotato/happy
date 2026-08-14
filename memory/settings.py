"""WHAT EVERY KNOB IS SET TO."""

import json
import threading
from datetime import datetime

from memory import catalogue, storage
from memory.knobs import settle

SAVE = "INSERT INTO settings (key, value, at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, at=excluded.at"

EVERYTHING = "SELECT key, value FROM settings"

DROP = "DELETE FROM settings WHERE key = ?"

held = None
stamp = 0
stamps = {}
lock = threading.Lock()


def version(group=None):
    """A NUMBER THAT ONLY GOES UP."""
    return stamps.get(group, 0) if group else stamp


def get(key, fallback=None):
    """WHAT THIS SETTING IS, OR WHAT THE CATALOGUE SAYS IT SHOULD BE."""
    kept = loaded()

    if key in kept:
        return kept[key]

    return catalogue.default(key) if fallback is None else fallback


def put(key, value):
    """SET ONE KNOB. RETURNS WHAT IT ACTUALLY ENDED UP AS."""
    entry = catalogue.entry(key)

    if entry is None:
        return None

    wanted = settle(entry, value)

    with lock:
        loaded()[key] = wanted
        bump(key)

    storage.write(SAVE, (key, json.dumps(wanted), now()))

    return wanted


def clear(key):
    """PUT ONE KNOB BACK TO WHAT IT SHIPPED AS."""
    with lock:
        loaded().pop(key, None)
        bump(key)

    storage.write(DROP, (key,))

    return catalogue.default(key)


def every():
    """EVERY KNOB AND ITS VALUE, THE UNTOUCHED ONES INCLUDED."""
    kept = loaded()

    return {key: kept.get(key, catalogue.default(key)) for key in catalogue.keys()}


def groups():
    """THE CATALOGUE, FOR SOMETHING THAT HAS TO DRAW THE CONTROLS."""
    return catalogue.GROUPS


def loaded():
    global held

    if held is None:
        held = read()

    return held


def read():
    """WHAT THE FILE HOLDS, THE UNREADABLE AND THE UNKNOWN LEFT OUT."""
    kept = {}

    try:
        rows = storage.read(EVERYTHING)
    except Exception:
        return kept

    for row in rows:
        entry = catalogue.entry(row["key"])

        if entry is None:  # A KNOB THAT USED TO EXIST. IGNORED, NOT DELETED.
            continue

        try:
            kept[row["key"]] = settle(entry, json.loads(row["value"]))
        except ValueError:
            continue

    return kept


def bump(key=None):
    """MARK EVERYTHING AS CHANGED, OR JUST THE GROUP THE KEY BELONGS TO."""
    global stamp

    stamp += 1

    for group in [key.split(".")[0]] if key else [each["key"] for each in catalogue.GROUPS]:
        stamps[group] = stamps.get(group, 0) + 1


def forget():
    """DROP WHAT IS HELD, SO THE NEXT READ GOES TO THE FILE. FOR TESTS."""
    global held

    held = None

    bump()


def now():
    return datetime.now().astimezone().isoformat(timespec="milliseconds")
