"""EVERY MESSAGE EVER SAID, AND HOW TO READ IT BACK.

ONE RUNNING CONVERSATION, NOT ONE PER SESSION. THE TIME IS A COLUMN AND NEVER A
HEADING, SO ASKING FOR LAST TUESDAY IS A QUERY AND NOT A PARSE.
"""

import json
from datetime import datetime

from memory import storage

YOU = "you"
HAPPY = "happy"
TOOL = "tool"

# A TOOL CAN HAND BACK A WHOLE PDF. THE CONVERSATION SHOULD STAY READABLE.
LIMIT = 2000
ELLIPSIS = "..."

INSERT = """
INSERT INTO messages (at, epoch, who, text, tool, args, seconds, audio, unprompted)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

RECENT = "SELECT * FROM messages ORDER BY epoch DESC LIMIT ?"
EVERYTHING = "SELECT * FROM messages ORDER BY epoch"
BETWEEN = "SELECT * FROM messages WHERE epoch BETWEEN ? AND ? ORDER BY epoch"

FIND = """
SELECT * FROM messages
WHERE text LIKE ? ESCAPE '\\'
ORDER BY epoch DESC LIMIT ?
"""

WILD = "%"

# % AND _ ARE WILDCARDS TO LIKE, SO SEARCHING FOR "75%" MUST NOT MATCH EVERYTHING.
ESCAPE = str.maketrans({"%": r"\%", "_": r"\_", "\\": r"\\"})


def add(who, text, tool=None, args=None, seconds=None, audio=None, unprompted=False, at=None):
    """ONE MESSAGE. NEVER RAISES, A LOST LINE IS NOT WORTH A LOST TURN."""
    stamp = at or datetime.now().astimezone()

    try:
        storage.write(
            INSERT,
            (
                stamp.isoformat(timespec="milliseconds"),
                stamp.timestamp(),
                who,
                text,
                tool,
                json.dumps(args, default=str) if args is not None else None,
                round(seconds, 3) if seconds is not None else None,
                str(audio) if audio is not None else None,
                int(bool(unprompted)),
            ),
        )
    except Exception:
        pass


def said(text, **about):
    add(YOU, text, **about)


def replied(text, **about):
    add(HAPPY, text, **about)


def used(name, args, result, seconds=None):
    """A TOOL CALL. WHAT IT WAS ASKED MATTERS AS MUCH AS WHAT IT ANSWERED."""
    add(TOOL, brief(result), tool=name, args=args, seconds=seconds)


def brief(result):
    text = result if isinstance(result, str) else str(result)

    return text if len(text) <= LIMIT else text[:LIMIT] + ELLIPSIS


def history(limit=None):
    """MESSAGES, OLDEST FIRST. limit TAKES THE LAST FEW INSTEAD OF ALL."""
    if limit is None:
        return [unpack(row) for row in storage.read(EVERYTHING)]

    return [unpack(row) for row in reversed(storage.read(RECENT, (limit,)))]


def since(start, end=None):
    """EVERYTHING BETWEEN TWO MOMENTS. TAKES datetime OR EPOCH SECONDS."""
    return [unpack(row) for row in storage.read(BETWEEN, (moment(start), moment(end)))]


def search(words, limit=50):
    """MESSAGES CONTAINING words, NEWEST FIRST. CASE DOES NOT MATTER."""
    wanted = (words or "").strip()

    if not wanted:
        return []

    pattern = WILD + wanted.translate(ESCAPE) + WILD

    return [unpack(row) for row in storage.read(FIND, (pattern, limit))]


def moment(value):
    if value is None:
        return datetime.now().astimezone().timestamp()

    return value.timestamp() if isinstance(value, datetime) else float(value)


def unpack(row):
    """A ROW AS A PLAIN DICT, WITH args BACK IN ITS REAL SHAPE."""
    entry = dict(row)

    if entry.get("args"):
        try:
            entry["args"] = json.loads(entry["args"])
        except ValueError:
            pass

    entry["unprompted"] = bool(entry.get("unprompted"))

    return {key: value for key, value in entry.items() if value not in (None, False)}
