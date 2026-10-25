"""Routines: a name for a few requests the person makes together, replayed as if they said them again."""

import json
import re
import time

from happy import history

SCHEMA = """
CREATE TABLE IF NOT EXISTS routines (
    id    INTEGER PRIMARY KEY,
    name  TEXT NOT NULL UNIQUE COLLATE NOCASE,
    steps TEXT NOT NULL,
    made  REAL NOT NULL
);
"""
RUN = re.compile(r"^(?:(?:please |can you |could you |hey )*(?:run|do|start|play|go through|kick off) )?(?:(?:my|the) )?(?P<name>.+?)(?: routine)?[.!?]*$", re.I)


def connect():
    db = history.connect()
    db.executescript(SCHEMA)
    return db


def shaped(row):
    return {**dict(row), "steps": json.loads(row["steps"])} if row else None


def every():
    with history.lock, connect() as db:
        return [shaped(r) for r in db.execute("SELECT * FROM routines ORDER BY name").fetchall()]


def named(name):
    """The routine with this name, said loosely: case, 'my' and a trailing 'routine' do not matter."""
    plain = re.sub(r"^(?:my|the) |\s+routine$", "", name.strip().lower())
    with history.lock, connect() as db:
        return shaped(db.execute("SELECT * FROM routines WHERE name = ?", (plain,)).fetchone())


def save(name, steps):
    plain = re.sub(r"^(?:my|the) |\s+routine$", "", name.strip().lower())
    with history.lock, connect() as db:
        db.execute("INSERT INTO routines (name, steps, made) VALUES (?, ?, ?) "
                   "ON CONFLICT(name) DO UPDATE SET steps = excluded.steps", (plain, json.dumps(steps), time.time()))
    return named(plain)


def rename(old, new):
    number = named(old)["id"]
    with history.lock, connect() as db:
        db.execute("UPDATE routines SET name = ? WHERE id = ?", (new.strip().lower(), number))


def forget(name):
    number = named(name)["id"]
    with history.lock, connect() as db:
        db.execute("DELETE FROM routines WHERE id = ?", (number,))


def request(routine):
    """The routine said as one request, which the brain then works through like any other."""
    steps = "\n".join(f"{n}. {step}" for n, step in enumerate(routine["steps"], 1))
    return (f"Run my {routine['name']} routine. Do each of these in order, then answer them all together in a few sentences:\n{steps}")


def asked_for(text):
    """The routine a request plainly names ('run my morning brief', 'morning brief'), or None."""
    match = RUN.match(text.strip())
    return named(match.group("name")) if match and len(match.group("name")) < 60 else None
