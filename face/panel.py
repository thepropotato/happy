"""THE WINDOW'S FACE: ONE JSON OBJECT PER LINE, WRITTEN TO STDOUT.

WHILE THIS FACE IS ATTACHED, STDOUT CARRIES NOTHING ELSE. ANYTHING MEANT FOR A
PERSON TO READ GOES TO STDERR, WHICH THE WINDOW LOGS AND NOBODY PARSES.

EVERY PART OF HAPPY REPORTS FROM ITS OWN THREAD, SO A LOCK GUARDS THE LINE AND
NOT THE MEANING: HALF OF ONE OBJECT INSIDE ANOTHER IS THE ONLY REAL HAZARD.
"""

import json
import sys
import threading

from face.turn import MODEL, Turn

LOADING = "loading"
IDLE = "idle"
LISTENING = "listening"
HEARING = "hearing"
THINKING = "thinking"
SPEAKING = "speaking"

WAIT_SECONDS = 300  # NOBODY ANSWERING IS A NO, EVENTUALLY.

turn = None
reply = ""

writing = threading.Lock()
asked = {}
counter = 0


def send(what, **fields):
    line = json.dumps({"is": what, **fields}, default=str)

    with writing:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()


def ready(**about):
    send("ready", **about)


def state(name):
    send("state", state=name)


def begin():
    global turn, reply

    turn = Turn()
    reply = ""

    state(HEARING)


def listening():
    state(LISTENING)


def said(text, seconds=None):
    if turn:
        turn.heard = seconds

    send("message", who="you", text=text, seconds=seconds)


def opening():
    if turn:
        turn.speaking = True

    state(THINKING)


def piece(text):
    global reply

    if turn and turn.first is None:
        turn.first = turn.seconds()
        state(SPEAKING)

    reply += text

    send("piece", text=text)


def step(kind, name, seconds):
    if turn is None:
        return

    if kind == MODEL:
        turn.thought = seconds
    else:
        turn.add(name, seconds)
        send("step", kind=kind, name=name, seconds=seconds)


def trouble(text):
    send("trouble", text=str(text))


def note(text):
    send("note", text=str(text))


def unprompted(text):
    send("message", who="happy", text=text, unprompted=True)


def level(value):
    send("level", level=round(value, 4))


def envelope(values, seconds):
    send("envelope", values=values, seconds=round(seconds, 3))


def hush():
    send("hush")


def end():
    if turn is None:
        return

    if reply.strip():
        send("message", who="happy", text=reply.strip())

    # A BRUSHED KEY HAS NOTHING TO ACCOUNT FOR, AND A PANEL FULL OF "TOTAL 64MS"
    # IS A PANEL NOBODY READS.
    if turn.heard is not None or turn.thought is not None:
        send("stats", **spent(turn))

    state(IDLE)


def spent(this):
    """WHERE THE TIME WENT, AS NUMBERS. THE TERMINAL FORMATS ITS OWN."""
    return {
        "heard": this.heard,
        "thought": None if this.thought is None else max(0.0, this.thought - this.spent()),
        "tools": [{"name": name, "seconds": taken} for name, taken in this.tools],
        "first": this.first,
        "total": this.seconds(),
    }


def confirm(what, reason):
    """ASK THE WINDOW, AND WAIT. THIS RUNS ON WHICHEVER THREAD CALLED A TOOL."""
    global counter

    with writing:
        counter += 1
        which = counter

    waiting = threading.Event()
    asked[which] = [waiting, False]

    send("confirm", id=which, what=what, reason=reason)
    waiting.wait(WAIT_SECONDS)

    return asked.pop(which, [None, False])[1]


def answered(which, yes):
    """THE WINDOW SAID YES OR NO. WAKE WHOEVER IS SITTING ON IT."""
    found = asked.get(which)

    if found:
        found[1] = bool(yes)
        found[0].set()
