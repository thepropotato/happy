"""THINGS THE PERSON ASKED TO BE TOLD LATER, AND WHEN LATER IS."""

import time
from datetime import datetime

from memory import storage

SAVE = """
INSERT INTO reminders (what, kind, said, rule, due, at, fired, done)
VALUES (?, ?, ?, ?, ?, ?, 0, 0)
"""

EVERYTHING = "SELECT * FROM reminders ORDER BY done, due"

WAITING = "SELECT * FROM reminders WHERE done = 0 ORDER BY due"

FINISHED = "SELECT * FROM reminders WHERE done = 1 ORDER BY due DESC"

OVERDUE = "SELECT * FROM reminders WHERE done = 0 AND due <= ? ORDER BY due"

ONE = "SELECT * FROM reminders WHERE id = ?"

MOVE = "UPDATE reminders SET due = ?, rule = ?, said = ?, at = ?, done = 0 WHERE id = ?"

REWORD = "UPDATE reminders SET what = ?, at = ? WHERE id = ?"

ROLL = "UPDATE reminders SET due = ?, fired = fired + 1 WHERE id = ?"

FINISH = "UPDATE reminders SET done = 1, fired = fired + 1 WHERE id = ?"

DROP = "DELETE FROM reminders WHERE id = ?"

SWEEP = "DELETE FROM reminders WHERE done = 1"

SAY, ROUTINE = "say", "routine"

# A COUNTER THAT ONLY GOES UP, SO A FACE KNOWS TO REDRAW.
turned = 0

# WHO ELSE WANTS TELLING WHEN ONE CHANGES.
told = None

# THE ONE SET OR MOVED LAST, WHICH IS WHAT "THAT ONE" MEANS WITH NOTHING NAMED. IT LIVES
# ONLY AS LONG AS HAPPY DOES: AFTER A RESTART THERE IS NO "THAT ONE" TO MEAN.
touched = None


def every():
    """EVERY REMINDER, WAITING ONES FIRST AND SOONEST FIRST WITHIN THAT."""
    return [dict(row) for row in storage.read(EVERYTHING)]


def waiting():
    """WHAT HAS NOT GONE OFF YET, SOONEST FIRST."""
    return [dict(row) for row in storage.read(WAITING)]


def done():
    """WHAT HAS BEEN AND GONE, MOST RECENT FIRST."""
    return [dict(row) for row in storage.read(FINISHED)]


def one(id):
    found = storage.read(ONE, (id,))

    return dict(found[0]) if found else None


def overdue(moment=None):
    """EVERYTHING DUE BY NOW AND NOT YET SEEN TO."""
    return [dict(row) for row in storage.read(OVERDUE, (moment or time.time(),))]


def save(what, due, said="", rule="", kind=SAY):
    """WRITE ONE DOWN. due IS AN EPOCH, rule IS WALL CLOCK OR EMPTY FOR A ONE OFF."""
    text = " ".join(str(what or "").split())

    if not text:
        return None

    made = storage.write(SAVE, (text, kind, str(said or "").strip(), rule, float(due), now()))

    handled(made)

    return one(made)


def move(id, due, rule=None, said=None):
    """THE SAME REMINDER AT A DIFFERENT TIME."""
    found = one(id)

    if not found:
        return None
    storage.write(MOVE, (
        float(due),
        found["rule"] if rule is None else rule,
        found["said"] if said is None else str(said or "").strip(),
        now(),
        id,
    ))

    handled(id)

    return one(id)


def reword(id, what):
    """THE SAME TIME, DIFFERENT WORDS."""
    text = " ".join(str(what or "").split())

    if not one(id) or not text:
        return None

    storage.write(REWORD, (text, now(), id))
    handled(id)

    return one(id)


def rolled(id, due):
    """A RECURRING ONE HAS GONE OFF AND IS SET FOR ITS NEXT TIME ROUND."""
    storage.write(ROLL, (float(due), id))
    bump()


def finished(id):
    """A ONE OFF HAS GONE OFF, OR HAS BEEN ACCOUNTED FOR. IT STAYS AS A RECORD."""
    storage.write(FINISH, (id,))
    bump()


def forget(id):
    found = one(id)

    if not found:
        return None

    global touched

    storage.write(DROP, (id,))

    if touched == id:
        touched = None

    bump()

    return found


def sweep():
    """CLEAR OUT EVERYTHING THAT HAS BEEN AND GONE. HOW MANY WENT."""
    gone = len(done())

    if gone:
        storage.write(SWEEP)
        bump()

    return gone



def handled(id):
    """THE ONE JUST SEEN TO, REMEMBERED FOR AS LONG AS THIS SESSION LASTS."""
    global touched

    touched = id

    bump()


def last():
    """THE REMINDER JUST SET, MOVED OR GONE OFF. WHAT "THAT ONE" MEANS WITH NOTHING NAMED.

    A FINISHED ONE COUNTS: "REMIND ME AGAIN IN TEN MINUTES" IS SAID TO ONE THAT HAS JUST
    THIS SECOND GONE OFF."""
    return one(touched) if touched else None


def whenever(callback):
    """WHO TO TELL WHEN ONE IS SET, MOVED, FIRED OR FORGOTTEN. ONE IS USUALLY MADE BY SAYING
    SO, AND A PANEL THAT WAS NEVER TOUCHED WOULD NEVER THINK TO ASK."""
    global told

    told = callback


def bump():
    global turned

    turned += 1

    if told:
        try:
            told()
        except Exception:  # NOBODY IS KEPT FROM SETTING ONE BY WHATEVER IS DRAWING.
            pass


def now():
    return datetime.now().astimezone().isoformat(timespec="milliseconds")
