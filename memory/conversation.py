"""EVERY EXCHANGE EVER HAD, AND HOW TO READ IT BACK."""

import contextvars
import json
from datetime import datetime

from memory import storage

# A PAGE READ OR A LIST OF SEARCH RESULTS IS THOUSANDS OF CHARACTERS, AND CLIPPING
# IT IS THROWING AWAY THE ONE THING THAT SAYS WHY A TURN WENT THE WAY IT DID.
LIMIT = 20000
ELLIPSIS = "..."

OPEN = """
INSERT INTO messages (at, epoch, message, audio, unprompted, tools)
VALUES (?, ?, ?, ?, ?, '[]')
"""

# '$[#]' IS THE SLOT PAST THE END OF THE ARRAY, SO ONE STATEMENT APPENDS WITHOUT
# READING THE COLUMN BACK. TWO TOOLS FINISHING AT ONCE CANNOT LOSE EITHER.
APPEND = "UPDATE messages SET tools = json_insert(tools, '$[#]', json(?)) WHERE id = ?"

CLOSE = "UPDATE messages SET reply = ?, seconds = ?, spent = ? WHERE id = ?"

RECENT = "SELECT * FROM messages ORDER BY epoch DESC LIMIT ?"
EVERYTHING = "SELECT * FROM messages ORDER BY epoch"
BETWEEN = "SELECT * FROM messages WHERE epoch BETWEEN ? AND ? ORDER BY epoch"

FIND = """
SELECT * FROM messages
WHERE message LIKE ? ESCAPE '\\' OR reply LIKE ? ESCAPE '\\'
ORDER BY epoch DESC LIMIT ?
"""

WILD = "%"

# % AND _ ARE WILDCARDS TO LIKE, SO SEARCHING FOR "75%" MUST NOT MATCH EVERYTHING.
ESCAPE = str.maketrans({"%": r"\%", "_": r"\_", "\\": r"\\"})

# WHICH ROW THE RUNNING TOOLS BELONG TO.
here = contextvars.ContextVar("exchange", default=None)

# HOW MUCH OF THE ANSWER HAD BEEN SAID WHEN A TOOL WAS REACHED FOR.
told = contextvars.ContextVar("told", default=0)


def begin(message=None, audio=None, unprompted=False, at=None):
    """OPEN AN EXCHANGE AND MAKE IT THE ONE TOOLS GET WRITTEN AGAINST."""
    stamp = at or datetime.now().astimezone()

    try:
        row = storage.write(
            OPEN,
            (
                stamp.isoformat(timespec="milliseconds"),
                stamp.timestamp(),
                message,
                str(audio) if audio is not None else None,
                int(bool(unprompted)),
            ),
        )
    except Exception:
        row = None

    here.set(row)
    told.set(0)

    return row


def progress(said):
    """HOW FAR THE ANSWER HAS GOT, IN CHARACTERS, FOR PINNING THE NEXT CALL."""
    told.set(said)


def asking():
    """WHAT THE PERSON SAID TO START THIS TURN, FOR A TOOL THAT HAS TO WEIGH IT."""
    row = here.get()

    if row is None:
        return None

    try:
        found = storage.read("SELECT message FROM messages WHERE id = ?", (row,))
    except Exception:
        return None

    return found[0][0] if found else None


def used(name, args, result, seconds=None, why=None, row=None, failed=False, spent=None):
    """ONE TOOL CALL, ONTO THE END OF ITS EXCHANGE'S LIST."""
    row = here.get() if row is None else row

    if row is None:
        return

    call = {
        "name": name,
        "why": why,
        "args": args,
        "result": brief(result),
        "failed": bool(failed),
        "seconds": round(seconds, 3) if seconds is not None else None,
        # WHAT THE ROUND THAT ASKED FOR THIS CALL COST, SO READING A TURN BACK
        # NEXT WEEK STILL SHOWS IT. None ON ANY BACKEND THAT WILL NOT SAY.
        "spent": spent,
        "after": told.get(),
    }

    try:
        storage.write(APPEND, (json.dumps(call, default=str), row))
    except Exception:
        pass


def close(reply, seconds=None, row=None, spent=None):
    """WHAT HAPPY ANSWERED, HOW LONG THE WHOLE EXCHANGE TOOK, AND WHAT IT COST."""
    row = here.get() if row is None else row

    if row is None:
        return

    try:
        storage.write(
            CLOSE,
            (
                reply,
                round(seconds, 3) if seconds is not None else None,
                json.dumps(spent) if spent else None,
                row,
            ),
        )
    except Exception:
        pass


def brief(result):
    text = result if isinstance(result, str) else str(result)

    return text if len(text) <= LIMIT else text[:LIMIT] + ELLIPSIS


def history(limit=None):
    """EXCHANGES, OLDEST FIRST. limit TAKES THE LAST FEW INSTEAD OF ALL."""
    if limit is None:
        return [unpack(row) for row in storage.read(EVERYTHING)]

    return [unpack(row) for row in reversed(storage.read(RECENT, (limit,)))]


def since(start, end=None):
    """EVERYTHING BETWEEN TWO MOMENTS. TAKES datetime OR EPOCH SECONDS."""
    return [unpack(row) for row in storage.read(BETWEEN, (moment(start), moment(end)))]


def search(words, limit=50):
    """EXCHANGES MENTIONING words, NEWEST FIRST. CASE DOES NOT MATTER."""
    wanted = (words or "").strip()

    if not wanted:
        return []

    pattern = WILD + wanted.translate(ESCAPE) + WILD

    return [unpack(row) for row in storage.read(FIND, (pattern, pattern, limit))]


def moment(value):
    if value is None:
        return datetime.now().astimezone().timestamp()

    return value.timestamp() if isinstance(value, datetime) else float(value)


def unpack(row):
    """A ROW AS A PLAIN DICT, WITH tools BACK IN ITS REAL SHAPE."""
    entry = dict(row)

    try:
        entry["tools"] = json.loads(entry.get("tools") or "[]")
    except ValueError:
        entry["tools"] = []

    # DROPPED ALTOGETHER BY THE LINE BELOW WHEN IT IS EMPTY, THE SAME AS EVERY OTHER
    # COLUMN NOTHING WAS WRITTEN TO.
    try:
        entry["spent"] = json.loads(entry["spent"]) if entry.get("spent") else None
    except (ValueError, TypeError):
        entry["spent"] = None

    entry["unprompted"] = bool(entry.get("unprompted"))

    return {key: value for key, value in entry.items() if value not in (None, False, [])}
