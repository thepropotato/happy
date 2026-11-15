"""Requests that worked once, kept as the exact steps they took, so the same words later run without a model."""

import json
import re
import time

from happy import history

# ACTIONS WHOSE RESULT SAYS WHAT HAPPENED. NOTHING THAT READS FOR AN ANSWER, SENDS, WRITES, DELETES OR HANDS OFF.
REPLAYABLE = {"use_app", "press_keys", "type_text", "open_app", "quit_app", "open_link", "open_file", "browser_tabs",
              "set_brightness", "set_volume", "set_keyboard_light", "media", "wifi"}
# WORDS IN A RESULT THAT MEAN THE STEP DID NOT DO WHAT WAS ASKED, OR COULD NOT BE SEEN TO.
FAILED = re.compile(r"^error|could not|couldn't|cannot|can't|nothing called|is not open|not somewhere to type|greyed out|"
                    r"no window|check before saying|needs accessibility|there is no|does not show|did not", re.I)
FORGET_AFTER = 60 * 24 * 3600
SCHEMA = """
CREATE TABLE IF NOT EXISTS learned (
    words TEXT PRIMARY KEY,
    steps TEXT NOT NULL,
    at    REAL NOT NULL,
    used  REAL NOT NULL,
    uses  INTEGER NOT NULL DEFAULT 0
);
"""


def connect():
    db = history.connect()
    db.executescript(SCHEMA)
    return db


def words(request):
    """The request as a key: lower case, no punctuation, without the name it was addressed by."""
    text = re.sub(r"[^\w'\s]", " ", request.lower())
    text = re.sub(r"^\s*(?:hey\s+)?happy\b", " ", text)
    text = re.sub(r"\b(?:please|pls|for me|now|thanks|thank you)\b", " ", text)
    return " ".join(text.split())


def worked(steps):
    """True when every step is a replayable action that reported success."""
    if not steps:
        return False
    for step in steps:
        if step.get("tool") not in REPLAYABLE or not step.get("ok"):
            return False
        if step["tool"] == "use_app" and (step.get("args") or {}).get("action") == "look":
            continue
        if FAILED.search(str(step.get("result", ""))):
            return False
    return True


def learn(request, steps):
    """Keeps the steps a request took when they all worked; True when it was kept."""
    key = words(request)
    acts = [{"tool": s["tool"], "args": s.get("args") or {}} for s in steps if not
            (s["tool"] == "use_app" and (s.get("args") or {}).get("action") == "look")]
    if not key or not worked(steps) or not acts:
        return False
    now = time.time()
    with history.lock, connect() as db:
        db.execute("INSERT INTO learned (words, steps, at, used) VALUES (?, ?, ?, ?) "
                   "ON CONFLICT(words) DO UPDATE SET steps = excluded.steps, at = excluded.at",
                   (key, json.dumps(acts), now, now))
    return True


def match(request):
    """The steps these words learned, or None; one unused for two months is let go."""
    key = words(request)
    if not key:
        return None
    with history.lock, connect() as db:
        db.execute("DELETE FROM learned WHERE used < ?", (time.time() - FORGET_AFTER,))
        row = db.execute("SELECT steps FROM learned WHERE words = ?", (key,)).fetchone()
    return json.loads(row["steps"]) if row else None


def used(request):
    with history.lock, connect() as db:
        db.execute("UPDATE learned SET used = ?, uses = uses + 1 WHERE words = ?", (time.time(), words(request)))


def forget(request):
    with history.lock, connect() as db:
        return db.execute("DELETE FROM learned WHERE words = ?", (words(request),)).rowcount > 0


def failed(result):
    return bool(FAILED.search(result or ""))
