"""Reminders kept in the history database: what, when it is due, and how it repeats."""

import json
import time
from datetime import datetime

from happy import history, timing

SCHEMA = """
CREATE TABLE IF NOT EXISTS reminders (
    id       INTEGER PRIMARY KEY,
    what     TEXT NOT NULL,
    due      REAL NOT NULL,
    rule     TEXT NOT NULL DEFAULT '',
    routine  TEXT NOT NULL DEFAULT '',
    made     REAL NOT NULL,
    fired    REAL,
    done     INTEGER NOT NULL DEFAULT 0
);
"""
# A REMINDER LATER THAN THIS WHEN IT FIRES WAS MISSED WHILE HAPPY WAS OFF OR THE LID WAS SHUT.
LATE = 120


def connect():
    db = history.connect()
    db.executescript(SCHEMA)
    return db


def shaped(row):
    if row is None:
        return None
    out = dict(row)
    out["rule"] = json.loads(out["rule"]) if out["rule"] else None
    out["at"] = datetime.fromtimestamp(out["due"])
    return out


def add(what, due, rule=None, routine=""):
    with history.lock, connect() as db:
        made = db.execute("INSERT INTO reminders (what, due, rule, routine, made) VALUES (?, ?, ?, ?, ?)",
                          (what, due.timestamp(), json.dumps(rule) if rule else "", routine, time.time())).lastrowid
    return get(made)


def get(number):
    with history.lock, connect() as db:
        return shaped(db.execute("SELECT * FROM reminders WHERE id = ?", (number,)).fetchone())


def upcoming():
    """Everything still to come, soonest first."""
    with history.lock, connect() as db:
        return [shaped(r) for r in db.execute("SELECT * FROM reminders WHERE done = 0 ORDER BY due").fetchall()]


def matching(words):
    """The reminders still to come whose words hold all the words given; all of them with none given."""
    wanted = [w for w in words.lower().split() if w not in ("the", "a", "my", "reminder", "to", "one", "about")]
    return [r for r in upcoming() if all(w in r["what"].lower() or w in (r["routine"] or "").lower() for w in wanted)]


def last_fired():
    with history.lock, connect() as db:
        return shaped(db.execute("SELECT * FROM reminders WHERE fired IS NOT NULL ORDER BY fired DESC LIMIT 1").fetchone())


def update(number, **fields):
    if "due" in fields and isinstance(fields["due"], datetime):
        fields["due"] = fields["due"].timestamp()
    if "rule" in fields:
        fields["rule"] = json.dumps(fields["rule"]) if fields["rule"] else ""
    sets = ", ".join(f"{name} = ?" for name in fields)
    with history.lock, connect() as db:
        db.execute(f"UPDATE reminders SET {sets} WHERE id = ?", (*fields.values(), number))
    return get(number)


def due(now=None):
    """The reminders whose time has come, each moved on to its next turn or finished, with whether it was missed."""
    now = now or datetime.now()
    with history.lock, connect() as db:
        rows = [shaped(r) for r in db.execute("SELECT * FROM reminders WHERE done = 0 AND due <= ? ORDER BY due",
                                              (now.timestamp(),)).fetchall()]
    fired = []
    for row in rows:
        missed = now.timestamp() - row["due"] > LATE
        if row["rule"]:
            # A REPEATING ONE MISSED SEVERAL TIMES COMES ROUND ONCE, THEN CARRIES ON FROM NOW.
            update(row["id"], due=timing.following(row["rule"], max(row["at"], now)), fired=now.timestamp())
        else:
            update(row["id"], done=1, fired=now.timestamp())
        fired.append({**row, "missed": missed})
    return fired


def described(row, now=None):
    """'call the dentist, 4 PM today' or 'drink water, every hour (next at 2 PM today)'."""
    when = timing.spoken(row["at"], now)
    if row["rule"]:
        return f"{row['what']}, {timing.spoken_rule(row['rule'])} (next {when})"
    return f"{row['what']}, {when}"
