"""Every conversation turn, kept in a local SQLite file so it can be looked back on."""

import json
import sqlite3
import threading
import time

from happy import paths

FILE = paths.HOME / "history.db"
lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS turns (
    id      INTEGER PRIMARY KEY,
    at      REAL NOT NULL,
    how     TEXT NOT NULL,
    request TEXT NOT NULL,
    reply   TEXT NOT NULL DEFAULT '',
    steps   TEXT NOT NULL DEFAULT '[]',
    model   TEXT NOT NULL DEFAULT '',
    seconds REAL,
    failed  INTEGER NOT NULL DEFAULT 0,
    unsaid  TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS turns_at ON turns(at);
CREATE TABLE IF NOT EXISTS trashed (
    id       INTEGER PRIMARY KEY,
    at       REAL NOT NULL,
    original TEXT NOT NULL,
    held     TEXT NOT NULL,
    restored INTEGER NOT NULL DEFAULT 0
);
"""


def connect():
    FILE.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(FILE, timeout=5)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    if "unsaid" not in {row["name"] for row in db.execute("PRAGMA table_info(turns)")}:
        db.execute("ALTER TABLE turns ADD COLUMN unsaid TEXT NOT NULL DEFAULT ''")
    return db


def begin(request, how, model=""):
    """Starts a turn and returns its id."""
    with lock, connect() as db:
        return db.execute("INSERT INTO turns (at, how, request, model) VALUES (?, ?, ?, ?)",
                          (time.time(), how, request, model)).lastrowid


def finish(turn, reply, steps, seconds, failed=False):
    with lock, connect() as db:
        db.execute("UPDATE turns SET reply = ?, steps = ?, seconds = ?, failed = ? WHERE id = ?",
                   (reply, json.dumps(steps, ensure_ascii=False, default=str), seconds, int(failed), turn))


def unsaid(turn, sentence):
    """Notes the sentence a reply was cut off in, so the part never heard is shown faded."""
    with lock, connect() as db:
        db.execute("UPDATE turns SET unsaid = ? WHERE id = ?", (sentence, turn))


def recent(limit=200, search=""):
    """Newest first, each with its steps decoded."""
    with lock, connect() as db:
        if search:
            like = f"%{search}%"
            rows = db.execute("SELECT * FROM turns WHERE request LIKE ? OR reply LIKE ? ORDER BY at DESC LIMIT ?",
                              (like, like, limit)).fetchall()
        else:
            rows = db.execute("SELECT * FROM turns ORDER BY at DESC LIMIT ?", (limit,)).fetchall()
    return [{**dict(row), "steps": json.loads(row["steps"] or "[]")} for row in rows]


def since(seconds):
    """Turns from the last few minutes, oldest first, to carry a conversation across a restart."""
    with lock, connect() as db:
        rows = db.execute("SELECT request, reply FROM turns WHERE at > ? AND reply != '' ORDER BY at",
                          (time.time() - seconds,)).fetchall()
    return [dict(row) for row in rows]


def trashed(original, held):
    """Notes something Happy moved to the Trash, so it can be put back."""
    with lock, connect() as db:
        db.execute("INSERT INTO trashed (at, original, held) VALUES (?, ?, ?)", (time.time(), original, held))


def trashed_matching(words):
    """The latest thing Happy deleted whose name holds the words, or the latest of all with none."""
    with lock, connect() as db:
        rows = db.execute("SELECT * FROM trashed WHERE restored = 0 ORDER BY at DESC").fetchall()
    wanted = words.lower().split()
    for row in rows:
        name = row["original"].rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
        if all(word in name for word in wanted):
            return dict(row)
    return None


def untrashed(row):
    with lock, connect() as db:
        db.execute("UPDATE trashed SET restored = 1 WHERE id = ?", (row,))
