"""WHAT IS CONNECTED, AND WHAT EACH SERVER LAST SAID IT COULD DO.

THOSE ARE THE SAME QUESTION. A SERVICE IS CONNECTED WHEN IT REMEMBERS TOOLS, AND
EVERY TOOL IT REMEMBERS GOES TO THE MODEL — THERE IS NO SWITCH IN BETWEEN.

THE TOOL LIST IS KEPT HERE ON PURPOSE. BINDING HAPPENS AT STARTUP AND MUST NEVER
WAIT ON A SUBPROCESS COMING UP, SO THE MODEL IS HANDED WHAT EACH SERVER OFFERED
LAST TIME WHILE THE SERVER ITSELF STARTS QUIETLY IN THE BACKGROUND.

THE SECRETS ARE NOT HERE. THEY LIVE IN A TABLE OWNED BY mcps/servers/shared/,
BECAUSE THE SERVERS READ IT THEMSELVES AND MUST NOT HAVE TO IMPORT ANY OF THIS.
"""

import json
from datetime import datetime

import memory.storage as storage

SCHEMA = """
CREATE TABLE IF NOT EXISTS connections (
    name  TEXT PRIMARY KEY,
    tools TEXT,
    state TEXT,
    at    TEXT NOT NULL
);
"""

# THE COLUMN THAT MARKS A TABLE OLD ENOUGH TO REBUILD RATHER THAN GROW INTO.
BEFORE = "enabled"

built = False


def setup():
    global built

    if built:
        return

    handle = storage.connect()

    with handle:
        reshape(handle)
        handle.executescript(SCHEMA)

    built = True
    tidy()


def reshape(handle):
    having = {row["name"] for row in handle.execute("PRAGMA table_info(connections)")}

    if BEFORE not in having:
        return

    # SWITCHED OFF COMES BACK AS NOT CONNECTED: TURNING SOMETHING ON THAT SOMEBODY
    # DELIBERATELY TURNED OFF IS THE WORSE OF THE TWO.
    kept = [
        (row["name"], row["tools"] if row["enabled"] else None)
        for row in handle.execute("SELECT name, enabled, tools FROM connections")
    ]

    handle.execute("DROP TABLE connections")
    handle.executescript(SCHEMA)

    for name, tools in kept:
        handle.execute(
            "INSERT INTO connections (name, tools, at) VALUES (?, ?, ?)", (name, tools, now())
        )


def tidy():
    """A CONNECTION TO A SERVICE HAPPY NO LONGER SHIPS, DROPPED WITH ITS SIGN IN."""
    from mcps import registry

    keeping = set(registry.names())

    for row in storage.read("SELECT name FROM connections"):
        if row["name"] not in keeping:
            forget(row["name"])


def add(name):
    """A ROW FOR A SERVICE THE FIRST TIME SOMEBODY TOUCHES IT. NEVER TOUCHES tools."""
    setup()
    storage.write(
        "INSERT INTO connections (name, at) VALUES (?, ?) ON CONFLICT(name) DO NOTHING",
        (name, now()),
    )

    return one(name)


def every():
    setup()

    return [unpacked(row) for row in storage.read("SELECT * FROM connections ORDER BY name")]


def one(name):
    setup()
    rows = storage.read("SELECT * FROM connections WHERE name = ?", (name,))

    return unpacked(rows[0]) if rows else None


def remember(name, tools):
    """WHAT THIS SERVER OFFERED, SO THE NEXT STARTUP DOES NOT HAVE TO ASK."""
    setup()
    storage.write(
        "UPDATE connections SET tools = ?, at = ? WHERE name = ?", (dumped(tools), now(), name)
    )


def mark(name, state):
    setup()
    storage.write("UPDATE connections SET state = ?, at = ? WHERE name = ?", (state, now(), name))


def forget(name):
    """DROP A CONNECTION AND ANYTHING IT WAS SIGNED IN WITH."""
    from mcps.servers.shared import credentials

    storage.write("DELETE FROM connections WHERE name = ?", (name,))
    credentials.forget(name)


def unpacked(row):
    return {
        "name": row["name"],
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
