"""
WHERE HAPPY KEEPS THINGS BETWEEN SESSIONS.

ONE SQLITE FILE. IT NEEDS NO SERVER, IT IS IN THE STANDARD LIBRARY, IT SURVIVES
A CRASH MID WRITE, AND IT ANSWERS QUESTIONS A FLAT FILE CANNOT: WHAT DID I SAY
ABOUT THE DENTIST, WHAT DID HE DO LAST TUESDAY, HOW OFTEN DOES THAT TOOL FAIL.
A LOG YOU CAN ONLY READ FROM THE BOTTOM IS NOT A MEMORY.

THIS MODULE OWNS THE FILE AND THE SHAPE OF IT. WHAT GOES IN THE TABLES IS
SOMEBODY ELSE'S BUSINESS, SO chat.py OWNS THE CONVERSATION AND WHATEVER COMES
NEXT OWNS ITS OWN TABLES ALONGSIDE.

EVERY THREAD GETS ITS OWN CONNECTION, BECAUSE SQLITE OBJECTS DO NOT TRAVEL AND
BECAUSE A BROWSER ERRAND FINISHING ON ITS OWN THREAD WRITES AT THE SAME MOMENT
THE VOICE LOOP DOES. WAL LETS THEM.
"""

import sqlite3
import threading
from pathlib import Path

FILE = Path(__file__).resolve().parent / "data" / "happy.db"

# HOW LONG A WRITER WAITS FOR ANOTHER WRITER BEFORE GIVING UP. GENEROUS, BECAUSE
# LOSING A LINE OF THE CONVERSATION IS WORSE THAN A MOMENT'S WAIT.
BUSY_TIMEOUT_MS = 5000

# ONE TABLE AND ONE INDEX. NOTHING ELSE APPEARS IN THIS FILE, WHICH IS THE POINT.
#
# THERE WAS AN FTS5 SEARCH INDEX HERE. IT WORKED, AND IT DRAGGED FOUR SHADOW
# TABLES AND THREE TRIGGERS IN BEHIND IT, ALL OF WHICH SQLITE CREATES ON YOUR
# BEHALF AND NONE OF WHICH YOU EVER READ. FOR ONE PERSON'S CONVERSATION THAT IS
# A LOT OF MACHINERY TO AVOID A SCAN THAT TAKES A SIXTH OF A SECOND OVER TWO
# HUNDRED THOUSAND MESSAGES. SEARCH IS A LIKE NOW, IN chat.search().
#
# THE INDEX EARNS ITS KEEP AND IS NOT A TABLE: WITHOUT IT, ASKING FOR THE NEWEST
# FIFTY MESSAGES SORTS THE WHOLE TABLE. MEASURED AT TWO HUNDRED THOUSAND ROWS,
# THAT IS 123 ms AGAINST 0.1 ms.
SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY,
    at         TEXT    NOT NULL,          -- ISO 8601, LOCAL, WITH THE OFFSET ON IT
    epoch      REAL    NOT NULL,          -- THE SAME MOMENT, FOR SORTING AND RANGES
    who        TEXT    NOT NULL,          -- you | happy | tool
    text       TEXT    NOT NULL,
    tool       TEXT,                      -- TOOL LINES ONLY
    args       TEXT,                      -- JSON, TOOL LINES ONLY
    seconds    REAL,                      -- HOW LONG THE TOOL TOOK
    audio      TEXT,                      -- THE WAV BEHIND A SPOKEN LINE
    unprompted INTEGER NOT NULL DEFAULT 0 -- HE SPOKE UP ON HIS OWN
);

CREATE INDEX IF NOT EXISTS messages_epoch ON messages(epoch);
"""

# WHAT AN OLDER HAPPY LEFT BEHIND. DROPPING THE VIRTUAL TABLE TAKES ITS FOUR
# SHADOW TABLES WITH IT. HARMLESS TO RUN ON A DATABASE THAT NEVER HAD THEM.
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
    """THIS THREAD'S CONNECTION, OPENED AND PREPARED THE FIRST TIME IT ASKS."""
    here = getattr(local, "handle", None)

    if here is not None and getattr(local, "file", None) == FILE:
        return here

    FILE.parent.mkdir(parents=True, exist_ok=True)

    handle = sqlite3.connect(FILE, timeout=BUSY_TIMEOUT_MS / 1000)
    handle.row_factory = sqlite3.Row

    # WAL LETS A READER READ WHILE A WRITER WRITES, WHICH IS THE WHOLE POINT
    # WHEN A BACKGROUND JOB CAN SPEAK MID CONVERSATION.
    handle.execute("PRAGMA journal_mode=WAL")
    handle.execute("PRAGMA synchronous=NORMAL")
    handle.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")

    if FILE not in built:
        handle.executescript(SCHEMA)
        handle.executescript(TIDY)  # ONCE PER FILE, AND A NO-OP EVER AFTER.
        handle.commit()
        built.add(FILE)

    local.handle, local.file = handle, FILE

    return handle


def write(sql, values=()):
    """ONE STATEMENT, COMMITTED. RETURNS THE NEW ROW'S ID."""
    handle = connect()

    with handle:  # COMMITS ON SUCCESS, ROLLS BACK ON A RAISE.
        return handle.execute(sql, values).lastrowid


def read(sql, values=()):
    return connect().execute(sql, values).fetchall()


def use(file):
    """POINT AT A DIFFERENT DATABASE. FOR TESTS, AND FOR NOTHING ELSE."""
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
