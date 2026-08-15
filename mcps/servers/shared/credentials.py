"""THE ACCOUNT A SERVER RUNS AS, READ STRAIGHT OUT OF data/happy.db.

A SIGN IN IS CHECKED ON THE WAY INTO EVERY TOOL CALL, NEVER ONCE AT STARTUP: A SERVER THAT
HAS BEEN UP SINCE THIS MORNING IS HOLDING AN ACCESS TOKEN THAT DIED AT LUNCHTIME. WHERE THERE
IS A WAY TO RENEW IT, IT IS RENEWED IN PLACE AND WRITTEN BACK BEFORE THE CALL GOES OUT, AND
WHERE THERE IS NOT, THE CALL IS REFUSED IN WORDS THAT SAY WHAT TO DO ABOUT IT."""

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path

FILE = Path(__file__).resolve().parents[3] / "data" / "happy.db"

# HOW LONG BEFORE ITS LAST MOMENT A TOKEN IS TREATED AS GONE. A CALL THAT TAKES A SECOND MUST
# NOT SET OUT ON A TOKEN WITH A SECOND LEFT ON IT.
MARGIN = 60

STALE = "{service} needs signing in again. Connect it in Happy's connections panel."

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
    """A CONNECTION OF THIS CALL'S OWN."""
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
    """SIGN OUT."""
    put(name, tokens={})


def forget(name):
    """EVERYTHING THIS SERVICE EVER HAD, GONE. FOR ONE HAPPY NO LONGER SHIPS."""
    handle = opened()

    try:
        handle.execute("DELETE FROM connection_secrets WHERE name = ?", (name,))
        handle.commit()
    finally:
        handle.close()


def token(name, renew=None, service=None):
    """THE ONE SECRET A SERVICE SIGNS IN WITH, GOOD AT THE MOMENT IT IS HANDED OVER.

    CALL THIS INSIDE THE TOOL, NEVER ABOVE IT: WHAT IT ANSWERS IS ONLY TRUE NOW. renew IS THE
    SERVICE'S OWN WAY OF GETTING ANOTHER ONE, BECAUSE ONLY THE SERVICE KNOWS HOW."""
    held = kept(name)
    tokens = held["tokens"] or {}

    if not tokens.get("access_token") and not tokens.get("refresh_token"):
        return ""  # NEVER SIGNED IN AT ALL, WHICH IS THE SERVER'S OWN MISSING TO SAY.

    if not spent(tokens):
        return tokens.get("access_token") or ""

    if renew is None:
        raise PermissionError(STALE.format(service=service or name))

    moved = renew(tokens, held["client"]) or {}

    if not moved.get("access_token"):
        raise PermissionError(STALE.format(service=service or name))

    put(name, tokens={**tokens, **moved})

    return moved["access_token"]


def spent(tokens):
    """TRUE WHEN THE TOKEN HAS RUN OUT. ONE THAT NEVER SAID IT WOULD IS TAKEN AT ITS WORD."""
    when = (tokens or {}).get("expires_at")

    if not when:
        return False

    try:
        return float(when) - MARGIN <= time.time()
    except (TypeError, ValueError):
        return False


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
