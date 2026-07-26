"""
THE CONVERSATION. EVERYTHING YOU HAVE EVER SAID TO HAPPY AND HE TO YOU.

ONE RUNNING CONVERSATION, NOT ONE PER DAY AND NOT ONE PER SESSION, BECAUSE
TALKING TO SOMEONE YOU LIVE WITH DOES NOT RESTART AT MIDNIGHT. THE TIME IS A
COLUMN ON THE MESSAGE AND NEVER A HEADING BETWEEN MESSAGES, SO ASKING FOR LAST
TUESDAY IS A QUERY AND NOT A PARSE.

THE ROWS LIVE IN store.py. WHAT A MESSAGE IS, AND HOW IT READS BACK, LIVES HERE.
"""

import json
from datetime import datetime

import store

YOU = "you"
HAPPY = "happy"
TOOL = "tool"

# A TOOL CAN HAND BACK A WHOLE PDF. THE CONVERSATION SHOULD STAY READABLE, AND
# THE REAL ANSWER ALREADY WENT TO THE MODEL WHEN IT MATTERED.
LIMIT = 2000
ELLIPSIS = "..."

INSERT = """
INSERT INTO messages (at, epoch, who, text, tool, args, seconds, audio, unprompted)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

RECENT = "SELECT * FROM messages ORDER BY epoch DESC LIMIT ?"
EVERYTHING = "SELECT * FROM messages ORDER BY epoch"
BETWEEN = "SELECT * FROM messages WHERE epoch BETWEEN ? AND ? ORDER BY epoch"

# A PLAIN SCAN. NO INDEX, NO SHADOW TABLES, NO STEMMING. OVER TWO HUNDRED
# THOUSAND MESSAGES IT TAKES ABOUT A SIXTH OF A SECOND, AND NOBODY WILL EVER SAY
# THAT MUCH TO HAPPY. WHAT IT COSTS IS RANKING AND WORD ENDINGS: "MEET" WILL NOT
# FIND "MEETING", SO THE % GOES ON BOTH SIDES AND THE CALLER TYPES LESS.
FIND = """
SELECT * FROM messages
WHERE text LIKE ? ESCAPE '\\'
ORDER BY epoch DESC LIMIT ?
"""

WILD = "%"

# % AND _ ARE WILDCARDS TO LIKE, SO A PERSON SEARCHING FOR "75%" MUST NOT GET
# EVERY MESSAGE. THE BACKSLASH ESCAPES ITSELF TOO, OR SEARCHING FOR A PATH
# WOULD LEAVE A DANGLING ESCAPE AT THE END OF THE PATTERN.
ESCAPE = str.maketrans({"%": r"\%", "_": r"\_", "\\": r"\\"})


def add(who, text, tool=None, args=None, seconds=None, audio=None, unprompted=False, at=None):
    """ONE MESSAGE. NEVER RAISES, A LOST LINE IS NOT WORTH A LOST TURN.

    at IS FOR CARRYING MESSAGES IN FROM SOMEWHERE ELSE WITH THEIR OWN TIMES ON
    THEM. LEAVE IT ALONE AND IT MEANS NOW, WHICH IS WHAT EVERY LIVE CALL WANTS.
    """
    stamp = at or datetime.now().astimezone()

    try:
        store.write(
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
    """MESSAGES, OLDEST FIRST. limit TAKES THE LAST FEW INSTEAD OF ALL OF THEM."""
    if limit is None:
        return [unpack(row) for row in store.read(EVERYTHING)]

    return [unpack(row) for row in reversed(store.read(RECENT, (limit,)))]


def since(start, end=None):
    """EVERYTHING BETWEEN TWO MOMENTS. TAKES datetime OR EPOCH SECONDS."""
    return [unpack(row) for row in store.read(BETWEEN, (moment(start), moment(end)))]


def search(words, limit=50):
    """MESSAGES CONTAINING words, NEWEST FIRST. CASE DOES NOT MATTER."""
    wanted = (words or "").strip()

    if not wanted:
        return []

    pattern = WILD + wanted.translate(ESCAPE) + WILD

    return [unpack(row) for row in store.read(FIND, (pattern, limit))]


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


def when(entry):
    try:
        return datetime.fromisoformat(entry["at"])
    except (KeyError, ValueError):
        return None


WIDTH = 5
NAMES = {YOU: "you", HAPPY: "happy", TOOL: "  ·"}


def show(entries=None, tools=False):
    """THE CONVERSATION AS A CHAT. TOOL CALLS ARE PLUMBING, HIDDEN BY DEFAULT."""
    lines = []

    for entry in history() if entries is None else entries:
        if entry.get("who") == TOOL and not tools:
            continue

        stamp = when(entry)
        clock = stamp.strftime("%d %b %H:%M") if stamp else "?"
        who = NAMES.get(entry.get("who"), entry.get("who", "?"))

        if entry.get("who") == TOOL:
            lines.append(f"{clock}  {who:>{WIDTH}}  {entry.get('tool')}({entry.get('args')})")
        else:
            lines.append(f"{clock}  {who:>{WIDTH}}  {entry.get('text', '')}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    words = [a for a in sys.argv[1:] if not a.startswith("--")]
    found = search(" ".join(words)) if words else None

    print(show(found, tools="--tools" in sys.argv) or f"Nothing said yet. ({store.path()})")
