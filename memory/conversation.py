"""EVERY EXCHANGE EVER HAD, AND HOW TO READ IT BACK.

ONE ROW IS ONE EXCHANGE: WHAT WAS SAID, WHAT CAME BACK, AND EVERY TOOL REACHED
FOR IN BETWEEN. THE CALLS BELONG TO THE ROW, SO PINNING FIVE OF THEM ON THE
SENTENCE THAT CAUSED THEM IS THE SHAPE OF THE TABLE AND NOT A QUERY.

ONE RUNNING CONVERSATION, NOT ONE PER SESSION. THE TIME IS A COLUMN AND NEVER A
HEADING, SO ASKING FOR LAST TUESDAY IS A QUERY AND NOT A PARSE.
"""

import contextvars
import json
from datetime import datetime

from memory import storage

LIMIT = 2000
ELLIPSIS = "..."

OPEN = """
INSERT INTO messages (at, epoch, message, audio, unprompted, tools)
VALUES (?, ?, ?, ?, ?, '[]')
"""

# '$[#]' IS THE SLOT PAST THE END OF THE ARRAY, SO ONE STATEMENT APPENDS WITHOUT
# READING THE COLUMN BACK. TWO TOOLS FINISHING AT ONCE CANNOT LOSE EITHER.
APPEND = "UPDATE messages SET tools = json_insert(tools, '$[#]', json(?)) WHERE id = ?"

CLOSE = "UPDATE messages SET reply = ?, seconds = ? WHERE id = ?"

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

# WHICH ROW THE TOOLS RUNNING RIGHT NOW BELONG TO. A CONTEXT VARIABLE BECAUSE THE
# MIDDLEWARE THAT SEES A CALL SITS INSIDE THE GRAPH, WITH NOWHERE TO BE HANDED IT.
here = contextvars.ContextVar("exchange", default=None)

# HOW MUCH OF THE ANSWER HAD BEEN SAID WHEN A TOOL WAS REACHED FOR. WITHOUT IT
# THE CALLS WOULD ALL PILE UP ABOVE THE WHOLE ANSWER WHEN A TURN IS REOPENED.
told = contextvars.ContextVar("told", default=0)


def begin(message=None, audio=None, unprompted=False, at=None):
    """OPEN AN EXCHANGE AND MAKE IT THE ONE TOOLS GET WRITTEN AGAINST.

    RETURNS THE ROW'S ID, OR None IF THE WRITE FAILED. NEVER RAISES, A LOST LINE
    IS NOT WORTH A LOST TURN.
    """
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


def used(name, args, result, seconds=None, why=None, row=None):
    """ONE TOOL CALL, ONTO THE END OF ITS EXCHANGE'S LIST."""
    row = here.get() if row is None else row

    if row is None:
        return

    call = {
        "name": name,
        "why": why,
        "args": args,
        "result": brief(result),
        "seconds": round(seconds, 3) if seconds is not None else None,
        "after": told.get(),
    }

    try:
        storage.write(APPEND, (json.dumps(call, default=str), row))
    except Exception:
        pass


def close(reply, seconds=None, row=None):
    """WHAT HAPPY ANSWERED, AND HOW LONG THE WHOLE EXCHANGE TOOK."""
    row = here.get() if row is None else row

    if row is None:
        return

    try:
        storage.write(CLOSE, (reply, round(seconds, 3) if seconds is not None else None, row))
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

    entry["unprompted"] = bool(entry.get("unprompted"))

    return {key: value for key, value in entry.items() if value not in (None, False, [])}
