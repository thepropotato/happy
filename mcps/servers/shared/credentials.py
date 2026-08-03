"""THE ACCOUNT A SERVER RUNS AS, READ STRAIGHT OUT OF data/happy.db.

EVERY SERVER IS ITS OWN PROCESS AND LOOKS ITS OWN CREDENTIALS UP HERE. NOTHING
IS HANDED OVER ON THE COMMAND LINE, WHERE EVERY ps ON THE MACHINE WOULD SEE IT,
AND NOTHING SITS IN A FILE BESIDE THE SERVER EITHER. THE PANEL WRITES THIS TABLE
AND THE SERVERS READ IT, WHICH IS WHY BOTH SIDES IMPORT THIS ONE MODULE.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

FILE = Path(__file__).resolve().parents[3] / "data" / "happy.db"

TABLE = """
CREATE TABLE IF NOT EXISTS connection_secrets (
    name   TEXT PRIMARY KEY,
    tokens TEXT,
    client TEXT,
    at     TEXT NOT NULL
)
"""

KEEP = """
INSERT INTO connection_secrets (name, tokens, client, at) VALUES (?, ?, ?, ?)
ON CONFLICT(name) DO UPDATE SET
    tokens=excluded.tokens, client=excluded.client, at=excluded.at
"""


def opened():
    """A CONNECTION OF THIS CALL'S OWN. SQLITE HANDLES DO NOT CROSS THREADS, AND A
    SERVER ANSWERS ON WHICHEVER ONE THE PROTOCOL HAPPENS TO BE ON."""
    FILE.parent.mkdir(parents=True, exist_ok=True)

    handle = sqlite3.connect(FILE, timeout=5)
    handle.row_factory = sqlite3.Row

    handle.execute("PRAGMA journal_mode=WAL")
    handle.execute("PRAGMA busy_timeout=5000")
    handle.execute(TABLE)

    return handle


def kept(name):
    """WHAT THIS SERVICE SIGNED IN WITH: ITS TOKENS, AND THE OAUTH CLIENT IF IT HAS ONE."""
    handle = opened()

    try:
        rows = handle.execute(
            "SELECT tokens, client FROM connection_secrets WHERE name = ?", (name,)
        ).fetchall()
    finally:
        handle.close()

    if not rows:
        return {"tokens": {}, "client": {}}

    return {"tokens": loaded(rows[0]["tokens"]), "client": loaded(rows[0]["client"])}


def put(name, **moved):
    held = kept(name)
    held.update(moved)

    handle = opened()

    try:
        handle.execute(KEEP, (name, dumped(held["tokens"]), dumped(held["client"]), now()))
        handle.commit()
    finally:
        handle.close()


def clear(name):
    """SIGN OUT. THE CLIENT SOMEBODY BROUGHT STAYS: THEY SPENT AN AFTERNOON ON IT,
    AND MAKING THEM FETCH IT AGAIN TO SIGN BACK IN IS NOT SIGNING OUT."""
    put(name, tokens={})


def forget(name):
    """EVERYTHING THIS SERVICE EVER HAD, GONE. FOR ONE HAPPY NO LONGER SHIPS."""
    handle = opened()

    try:
        handle.execute("DELETE FROM connection_secrets WHERE name = ?", (name,))
        handle.commit()
    finally:
        handle.close()


def token(name):
    """THE ONE PASTED SECRET A SERVICE SIGNS IN WITH, FOR THE ONES THAT ONLY WANT ONE."""
    return (kept(name)["tokens"] or {}).get("access_token") or ""


def dumped(value):
    return json.dumps(value or {})


def loaded(value):
    if not value:
        return {}

    try:
        held = json.loads(value)
    except ValueError:
        return {}

    return held if isinstance(held, dict) else {}


def now():
    return datetime.now().astimezone().isoformat(timespec="milliseconds")
