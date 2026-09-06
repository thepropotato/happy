"""THE SQLITE FILE. IT OWNS THE FILE AND THE SHAPE OF IT, NOTHING ELSE."""

import os
import sqlite3
import threading
from pathlib import Path

# TESTS POINT HAPPY_DB AT A THROWAWAY FILE SO A RUN NEVER LANDS IN THE REAL HISTORY.
ENV = "HAPPY_DB"

FILE = (Path(os.environ[ENV]).expanduser().resolve() if os.environ.get(ENV)
        else Path(__file__).resolve().parent.parent / "data" / "happy.db")

BUSY_TIMEOUT_MS = 5000

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY,
    at         TEXT    NOT NULL,
    epoch      REAL    NOT NULL,
    message    TEXT,
    reply      TEXT,
    tools      TEXT    NOT NULL DEFAULT '[]' CHECK (json_valid(tools)),
    audio      TEXT,
    seconds    REAL,
    unprompted INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS messages_epoch ON messages(epoch);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS routines (
    name        TEXT PRIMARY KEY,
    description TEXT NOT NULL DEFAULT '',
    steps       TEXT NOT NULL DEFAULT '',
    tools       TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(tools)),
    examples    TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(examples)),
    result      TEXT NOT NULL DEFAULT '',
    asked       TEXT NOT NULL DEFAULT '',
    at          TEXT NOT NULL,
    runs        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reminders (
    id     INTEGER PRIMARY KEY,
    what   TEXT    NOT NULL,
    kind   TEXT    NOT NULL DEFAULT 'say',
    said   TEXT    NOT NULL DEFAULT '',
    rule   TEXT    NOT NULL DEFAULT '',
    due    REAL    NOT NULL,
    at     TEXT    NOT NULL,
    fired  INTEGER NOT NULL DEFAULT 0,
    done   INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS reminders_due ON reminders(due);
"""

# WHAT AN OLDER HAPPY LEFT BEHIND. A NO-OP ON A DATABASE THAT NEVER HAD IT.
TIDY = """
DROP TRIGGER IF EXISTS messages_after_insert;
DROP TRIGGER IF EXISTS messages_after_delete;
DROP TRIGGER IF EXISTS messages_after_update;
DROP TABLE   IF EXISTS messages_search;
DROP INDEX   IF EXISTS messages_who;
DROP TABLE   IF EXISTS turns;
"""

BEFORE = "who"
SHAPE = "PRAGMA table_info(messages)"
DROP = "DROP TABLE IF EXISTS messages"

# A COLUMN ADDED TO A TABLE THAT ALREADY EXISTS, WHICH CREATE TABLE IF NOT EXISTS WILL NOT DO.
WIDER = [
    ("routines", "asked", "TEXT NOT NULL DEFAULT ''"),
    # WHAT THE TURN ITSELF COST. THE TOOL ROWS CARRY THEIR OWN; THE ROUND THAT ANSWERED
    # WITHOUT CALLING ONE HAD NOWHERE TO BE WRITTEN DOWN, SO A QUIET TURN CAME BACK FROM
    # THE DATABASE WITH A CLOCK AND NOTHING ELSE.
    ("messages", "spent", "TEXT"),
]


def reshape(handle):
    """CLEAR OUT A messages FROM BEFORE A ROW MEANT A WHOLE EXCHANGE."""
    if BEFORE in {row["name"] for row in handle.execute(SHAPE)}:
        handle.execute(DROP)


def widen(handle):
    """WHAT A LATER HAPPY WANTS THAT AN EARLIER ONE'S TABLE HAS NOT GOT."""
    for table, column, kind in WIDER:
        here = {row["name"] for row in handle.execute(f"PRAGMA table_info({table})")}

        if column not in here:
            handle.execute(f"ALTER TABLE {table} ADD COLUMN {column} {kind}")

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
        reshape(handle)  # BEFORE THE SCHEMA, SO THE NEW TABLE IS THE ONE CREATED.
        handle.executescript(SCHEMA)
        handle.executescript(TIDY)
        widen(handle)  # AFTER THE SCHEMA: A COLUMN NEEDS ITS TABLE THERE FIRST.
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
