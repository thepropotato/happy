"""THE WINDOW'S FACE: ONE JSON OBJECT PER LINE, WRITTEN TO STDOUT.

WHILE THIS FACE IS ATTACHED, STDOUT CARRIES NOTHING ELSE. ANYTHING MEANT FOR A
PERSON TO READ GOES TO STDERR, WHICH THE WINDOW LOGS AND NOBODY PARSES.

EVERY PART OF HAPPY REPORTS FROM ITS OWN THREAD, SO A LOCK GUARDS THE LINE AND
NOT THE MEANING: HALF OF ONE OBJECT INSIDE ANOTHER IS THE ONLY REAL HAZARD.
"""

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
    """TAKE THE PIPE TO THE WINDOW AND LEAVE EVERYONE ELSE POINTING AT STDERR.

    THE RULE ABOVE — STDOUT CARRIES NOTHING BUT JSON — IS NOT SOMETHING PYTHON
    CAN KEEP ON ITS OWN. HALF OF WHAT IS LOADED HERE IS C, AND C WRITES TO FILE
    DESCRIPTOR ONE WITHOUT ASKING: PORTAUDIO PRINTS ITS COREAUDIO GRUMBLES THERE
    ("||PaMacCore (AUHAL)|| Error on line 2796"), WHICH THE WINDOW THEN READS AS
    A MESSAGE FROM HAPPY AND CANNOT PARSE. WORSE, IT LANDS MID LINE AS EASILY AS
    BETWEEN TWO, AND A JSON OBJECT WITH A COMPLAINT WEDGED INTO IT IS LOST.

    SO THE PIPE IS DUPLICATED ONTO A DESCRIPTOR NOBODY ELSE KNOWS ABOUT, AND
    DESCRIPTOR ONE IS POINTED AT STDERR. EVERY printf IN EVERY LIBRARY NOW GOES
    WHERE THE REST OF THE NOISE ALREADY GOES — THE LOG — AND SO DOES ANY STRAY
    print() FROM THIS SIDE, BECAUSE sys.stdout STILL MEANS DESCRIPTOR ONE.
    """
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
    """HIS NAME LANDED ON ITS OWN. THE ONE THING THE EARS SAY OUT LOUD.

    NOT EVERY TIME THE MICROPHONE HEARS SOMETHING: THAT IS THE ROOM, AND THE
    WINDOW IS NOT A LEVEL METER.
    """
    state(LISTENING)


def idle():
    """HE WAITED AND NOBODY SAID THE REST.

    ONLY UNDOES listening. A TURN MAY HAVE STARTED IN THE MEANTIME — TYPED INTO
    THE BOX, OR SAID — AND THINKING IS NOT A STATE THE EARS GET TO END.
    """
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
        # ADDED UP AND SENT NOWHERE YET. THE ROUND'S OWN COST TRAVELS ON THE CALL
        # IT ASKED FOR; THE TOTAL GOES OUT WITH THE STATS AT THE END, WHICH IS THE
        # ONLY POINT THE LAST ROUND OF ALL — THE ONE THAT ANSWERS — IS IN IT.
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
