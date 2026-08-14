"""A CODER'S STREAM, READ WHILE IT IS STILL RUNNING."""

import json

# THE FIELD OF A TOOL'S INPUT THAT SAYS WHAT THE CALL IS ABOUT.
SUBJECT = {
    "Bash": "command",
    "Read": "file_path",
    "Write": "file_path",
    "Edit": "file_path",
    "Glob": "pattern",
    "Grep": "pattern",
    "WebFetch": "url",
    "WebSearch": "query",
    "Task": "description",
}

# LONG ENOUGH TO SAY WHICH FILE, SHORT ENOUGH TO SIT ON ONE ROW.
MOST = 70

OPENED = "Opened the project"

STOPPED = "the coder stopped early"


def follow(stream, watching):
    """READ THE OUTPUT LINE BY LINE, SAY WHAT IT DOES, AND HAND BACK HOW IT ENDED."""
    found = {}

    for raw in stream:
        event = parsed(raw)

        if event is None:
            continue

        keep(found, event)

        for said in lines(event):
            watching(said)

    return found


def parsed(raw):
    """ONE LINE AS AN EVENT, OR None IF IT WAS NOT ONE."""
    raw = raw.strip()

    if not raw:
        return None

    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        return None

    return event if isinstance(event, dict) else None


def keep(found, event):
    """WHAT THIS EVENT SETTLES: THE SESSION IT BELONGS TO, AND HOW IT ENDED."""
    # TAKEN FROM THE FIRST LINE AND EVERY ONE AFTER, SO A JOB KILLED PART WAY
    # THROUGH STILL LEAVES A SESSION TO GO BACK TO.
    session_id = event.get("session_id")

    if session_id:
        found["session_id"] = session_id

    if event.get("type") != "result":
        return

    answer = event.get("result")

    if event.get("is_error"):
        found["failed"] = answer or event.get("subtype") or STOPPED
    else:
        found["answer"] = answer


def lines(event):
    """WHAT THIS EVENT IS WORTH SAYING ON THE FACE, WHICH IS USUALLY NOTHING."""
    kind = event.get("type")

    if kind == "system" and event.get("subtype") == "init":
        return [OPENED]

    if kind != "assistant":
        return []

    said = [spoken(block) for block in content(event)]

    return [each for each in said if each]


def content(event):
    """THE BLOCKS OF ONE MESSAGE, WHATEVER SHAPE THE EVENT ARRIVED IN."""
    message = event.get("message")
    blocks = message.get("content") if isinstance(message, dict) else None

    return [each for each in blocks or [] if isinstance(each, dict)]


def spoken(block):
    """ONE BLOCK AS A LINE: A TOOL AND WHAT IT TOUCHED, OR WHAT THE CODER SAID."""
    if block.get("type") == "tool_use":
        return doing(block)

    return brief(block.get("text")) if block.get("type") == "text" else ""


def doing(block):
    """ONE TOOL CALL AS ITS NAME AND THE THING IT IS ABOUT."""
    name = block.get("name") or "working"
    asked = block.get("input")
    about = asked.get(SUBJECT.get(name, "")) if isinstance(asked, dict) else None

    return f"{name} {brief(about)}".strip()


def brief(text):
    """ONE LINE, WHITESPACE COLLAPSED, CUT WHERE IT STOPS FITTING."""
    said = " ".join(str(text or "").split())

    return f"{said[:MOST - 1]}…" if len(said) > MOST else said
