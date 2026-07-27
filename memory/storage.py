"""THE SQLITE FILE. IT OWNS THE FILE AND THE SHAPE OF IT, NOTHING ELSE."""

import sqlite3
import threading
from pathlib import Path

FILE = Path(__file__).resolve().parent.parent / "data" / "happy.db"

BUSY_TIMEOUT_MS = 5000

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY,
    at         TEXT    NOT NULL,
    epoch      REAL    NOT NULL,
    who        TEXT    NOT NULL,
    text       TEXT    NOT NULL,
    tool       TEXT,
    args       TEXT,
    seconds    REAL,
    audio      TEXT,
    unprompted INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS messages_epoch ON messages(epoch);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    at    TEXT NOT NULL
);
"""

# WHAT AN OLDER HAPPY LEFT BEHIND. A NO-OP ON A DATABASE THAT NEVER HAD IT.
TIDY = """
DROP TRIGGER IF EXISTS messages_after_insert;
DROP TRIGGER IF EXISTS messages_after_delete;
DROP TRIGGER IF EXISTS messages_after_update;
DROP TABLE   IF EXISTS messages_search;
DROP INDEX   IF EXISTS messages_who;
"""

local = threading.local()
built = set()


def path():
    return FILE


def connect():
    """THIS THREAD'S CONNECTION. SQLITE OBJECTS DO NOT TRAVEL BETWEEN THREADS."""
    here = getattr(local, "handle", None)

    if here is not None and getattr(local, "file", None) == FILE:
        return here

    FILE.parent.mkdir(parents=True, exist_ok=True)

    handle = sqlite3.connect(FILE, timeout=BUSY_TIMEOUT_MS / 1000)
    handle.row_factory = sqlite3.Row

    # WAL LETS A READER READ WHILE A WRITER WRITES.
    handle.execute("PRAGMA journal_mode=WAL")
    handle.execute("PRAGMA synchronous=NORMAL")
    handle.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")

    if FILE not in built:
        handle.executescript(SCHEMA)
        handle.executescript(TIDY)
        handle.commit()
        built.add(FILE)

    local.handle, local.file = handle, FILE

    return handle


def write(sql, values=()):
    """ONE STATEMENT, COMMITTED. RETURNS THE NEW ROW'S ID."""
    handle = connect()

    with handle:
        return handle.execute(sql, values).lastrowid


def read(sql, values=()):
    return connect().execute(sql, values).fetchall()


def use(file):
    """POINT AT A DIFFERENT DATABASE. FOR TESTS."""
    global FILE

    FILE = Path(file)
    local.handle = None

    return FILE


def forget():
    """CLOSE THIS THREAD'S CONNECTION. THE FILE IS UNTOUCHED."""
    handle = getattr(local, "handle", None)

    if handle is not None:
        handle.close()
        local.handle = None
