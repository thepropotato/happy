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
    failed  INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS turns_at ON turns(at);
"""


def connect():
    FILE.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(FILE, timeout=5)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
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
