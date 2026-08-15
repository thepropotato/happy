"""THE WINDOW'S FACE: ONE JSON OBJECT PER LINE, WRITTEN TO STDOUT."""

import json
import os
import sys
import threading

from face.turn import MODEL, SPENT, STARTED, Turn

LOADING = "loading"
IDLE = "idle"
LISTENING = "listening"
HEARING = "hearing"
THINKING = "thinking"
SPEAKING = "speaking"

turn = None
reply = ""
showing = LOADING  # THE LAST STATE THE WINDOW WAS PUT IN.

writing = threading.Lock()

# WHERE THE JSON GOES. STDOUT UNTIL only() TAKES THE PIPE SOMEWHERE PRIVATE.
channel = sys.stdout


def only():
    """TAKE THE PIPE TO THE WINDOW AND LEAVE EVERYONE ELSE POINTING AT STDERR."""
    global channel

    if channel is not sys.stdout:
        return

    kept = os.dup(sys.stdout.fileno())

    sys.stdout.flush()
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())

    channel = os.fdopen(kept, "w", encoding="utf-8")


def send(what, /, **fields):
    """POSITIONAL ONLY, SO A LINE MAY CARRY A FIELD OF ITS OWN CALLED "what"."""
    line = json.dumps({"is": what, **fields}, default=str)

    with writing:
        channel.write(line + "\n")
        channel.flush()


def ready(**about):
    send("ready", **about)


def state(name):
    global showing

    showing = name

    send("state", state=name)


def begin():
    global turn, reply

    turn = Turn()
    reply = ""

    state(HEARING)


def listening():
    """HIS NAME LANDED ON ITS OWN."""
    state(LISTENING)


def idle():
    """HE WAITED AND NOBODY SAID THE REST."""
    if showing == LISTENING:
        state(IDLE)


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


def step(kind, name, seconds, about=None):
    if turn is None:
        return

    # THE ID TIES THE STARTED AND FINISHED LINES TO THE ONE ROW.
    if kind == STARTED:
        send("began", name=name, **(about or {}))
    elif kind == SPENT:
        # ADDED UP AND SENT NOWHERE YET.
        turn.paid(about)
    elif kind == MODEL:
        turn.thought = seconds
    else:
        turn.add(name, seconds)
        send("step", kind=kind, name=name, seconds=seconds, **(about or {}))


def trouble(text):
    send("trouble", text=str(text))


def unprompted(text):
    send("message", who="happy", text=text, unprompted=True)


def working(text):
    send("working", text=text)


def level(value):
    send("level", level=round(value, 4))


def envelope(values, seconds):
    send("envelope", values=values, seconds=round(seconds, 3))


def hush():
    send("hush")


def end():
    if turn is None:
        return

    # THE PIECES ALREADY CARRIED EVERY WORD.
    send("done", spoke=bool(reply.strip()))

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
        "read": this.read,
        "wrote": this.wrote,
    }
