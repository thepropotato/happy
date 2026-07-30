"""WHAT IS CONNECTED, AND WHAT EACH ONE LAST SAID IT COULD DO.

THE TOOL LIST IS KEPT HERE ON PURPOSE. BINDING HAPPENS AT STARTUP AND MUST NEVER
WAIT ON A NETWORK, SO THE MODEL IS HANDED WHAT THE SERVER OFFERED LAST TIME WHILE
THE CONNECTION ITSELF COMES UP QUIETLY IN THE BACKGROUND.

SECRETS SIT IN THEIR OWN TABLE SO THEY CAN MOVE SOMEWHERE SAFER LATER WITHOUT
EVERY OTHER READ AND WRITE HAVING TO KNOW ABOUT IT.
"""

import json
from datetime import datetime

import memory.storage as storage

SCHEMA = """
CREATE TABLE IF NOT EXISTS connections (
    name    TEXT PRIMARY KEY,
    label   TEXT NOT NULL,
    kind    TEXT NOT NULL,
    address TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 0,
    allowed TEXT,
    tools   TEXT,
    state   TEXT,
    at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS connection_secrets (
    name   TEXT PRIMARY KEY,
    tokens TEXT,
    client TEXT,
    at     TEXT NOT NULL
);
"""

SAVE = """
INSERT INTO connections (name, label, kind, address, enabled, allowed, tools, state, at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(name) DO UPDATE SET
    label=excluded.label, kind=excluded.kind, address=excluded.address,
    allowed=excluded.allowed, at=excluded.at
"""

KEEP = """
INSERT INTO connection_secrets (name, tokens, client, at) VALUES (?, ?, ?, ?)
ON CONFLICT(name) DO UPDATE SET tokens=excluded.tokens, client=excluded.client, at=excluded.at
"""

built = False


def setup():
    global built

    if built:
        return

    handle = storage.connect()

    with handle:
        handle.executescript(SCHEMA)

    built = True


def save(name, label, kind, address, allowed=None):
    """ADD A CONNECTION, OR UPDATE HOW TO REACH ONE. NEVER TOUCHES enabled."""
    setup()
    storage.write(
        SAVE,
        (name, label, kind, address, 0, dumped(allowed), None, None, now()),
    )


def every():
    setup()

    return [unpacked(row) for row in storage.read("SELECT * FROM connections ORDER BY name")]


def one(name):
    setup()
    rows = storage.read("SELECT * FROM connections WHERE name = ?", (name,))

    return unpacked(rows[0]) if rows else None


def switch(name, enabled):
    setup()
    storage.write(
        "UPDATE connections SET enabled = ?, at = ? WHERE name = ?",
        (1 if enabled else 0, now(), name),
    )


def remember(name, tools):
    """WHAT THIS SERVER OFFERED, SO THE NEXT STARTUP DOES NOT HAVE TO ASK."""
    setup()
    storage.write(
        "UPDATE connections SET tools = ?, at = ? WHERE name = ?",
        (dumped(tools), now(), name),
    )


def mark(name, state):
    setup()
    storage.write(
        "UPDATE connections SET state = ?, at = ? WHERE name = ?", (state, now(), name)
    )


def forget(name):
    """DROP A CONNECTION AND ANYTHING IT WAS SIGNED IN WITH."""
    setup()
    storage.write("DELETE FROM connections WHERE name = ?", (name,))
    storage.write("DELETE FROM connection_secrets WHERE name = ?", (name,))


def keep(name, tokens=None, client=None):
    setup()
    storage.write(KEEP, (name, dumped(tokens), dumped(client), now()))


def secret(name):
    setup()
    rows = storage.read("SELECT tokens, client FROM connection_secrets WHERE name = ?", (name,))

    if not rows:
        return {}

    return {"tokens": loaded(rows[0]["tokens"]), "client": loaded(rows[0]["client"])}


def unpacked(row):
    return {
        "name": row["name"],
        "label": row["label"],
        "kind": row["kind"],
        "address": row["address"],
        "enabled": bool(row["enabled"]),
        "allowed": loaded(row["allowed"]) or [],
        "tools": loaded(row["tools"]) or [],
        "state": row["state"],
    }


def dumped(value):
    return None if value is None else json.dumps(value)


def loaded(value):
    if not value:
        return None

    try:
        return json.loads(value)
    except ValueError:
        return None


def now():
    return datetime.now().astimezone().isoformat(timespec="milliseconds")
