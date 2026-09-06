"""WHAT THE TERMINAL SHOWS."""

import shutil
from datetime import datetime

from face.turn import MODEL, SPENT, STARTED, Turn, stats

WIDTH = 78
RULE = "─"

YOU = "you"
HAPPY = "happy"

DIM = "\033[2m"
BOLD = "\033[1m"
OFF = "\033[0m"

LABEL = 6  # "happy " AND "you   " LINE UP.

turn = None
waiting = False  # THE "listening" LINE IS SITTING ON THE TERMINAL RIGHT NOW.


def width():
    return min(shutil.get_terminal_size((WIDTH, 24)).columns, WIDTH)


def wipe():
    print("\r" + " " * width() + "\r", end="")


def rule():
    stamp = datetime.now().strftime("%H:%M:%S")

    print(f"\n{DIM}{RULE * max(0, width() - len(stamp) - 1)} {stamp}{OFF}")


def begin():
    global turn, waiting

    turn = Turn()
    waiting = False

    wipe()
    rule()


def listening():
    """THE KEY IS DOWN AND WHATEVER IS BEING SAID INTO IT IS BEING KEPT."""
    global waiting

    waiting = True

    print(f"{DIM}{'':<{LABEL}}listening{OFF}", end="\r", flush=True)


def idle():
    """HE WAITED AND NOBODY SAID THE REST."""
    global waiting

    if not waiting:
        return

    waiting = False

    wipe()


def said(text, seconds=None):
    if turn:
        turn.heard = seconds

    print(f"{BOLD}{YOU:<{LABEL}}{OFF}{text}")


def opening():
    if turn:
        turn.speaking = True

    print(f"{BOLD}{HAPPY:<{LABEL}}{OFF}", end="", flush=True)


def piece(text):
    """ONE PIECE OF THE REPLY. THE FIRST ONE STOPS A STOPWATCH."""
    if turn and turn.first is None:
        turn.first = turn.seconds()

    print(text, end="", flush=True)


def cost():
    """WHAT THIS TURN COST, FOR WRITING DOWN BESIDE IT.

    THE CLOCKS THAT CANNOT BE WORKED OUT AGAIN FROM THE ROW GO IN HERE TOO: total IS THE
    seconds COLUMN AND THE TOOL TIMES ARE ON THE TOOL ROWS, BUT HOW LONG IT LISTENED, HOW
    LONG IT THOUGHT AND HOW SOON IT SPOKE ARE ONLY EVER HELD HERE."""
    if turn is None:
        return None

    kept = {
        "read": turn.read,
        "wrote": turn.wrote,
        "prefill": turn.prefill or None,
        "heard": turn.heard,
        "thought": None if turn.thought is None else max(0.0, turn.thought - turn.spent()),
        "first": turn.first,
    }

    return {key: value for key, value in kept.items() if value} or None


def step(kind, name, seconds, about=None):
    """WHAT brain.watches() FEEDS."""
    if turn is None:
        return

    # A CALL THAT HAS MERELY STARTED CARRIES NO TIME AND MUST NOT BE ADDED UP.
    if kind == STARTED:
        return

    if kind == SPENT:
        turn.paid(about)
    elif kind == MODEL:
        turn.thought = seconds
    else:
        turn.add(name, seconds)


def trouble(text):
    print(f"\n{DIM}{'':<{LABEL}}{text}{OFF}")


def end():
    if turn is None:
        return

    if turn.speaking:
        print()

    for line in stats(turn):
        print(f"{DIM}{'':<{LABEL}}{line}{OFF}")


def working(text):
    """WORK STILL GOING, INDENTED UNDER THE EXCHANGE THAT ASKED FOR IT."""
    print(f"{DIM}{'':<{LABEL}}{text}{OFF}")


def waking():
    """A TURN NOBODY ASKED FOR STARTS THE SAME WAY HERE AS ANY OTHER."""
    begin()


def unprompted(text):
    """WORK THAT FINISHED ON ITS OWN GETS ITS OWN BLOCK, NOT SOMEONE ELSE'S."""
    stamp = datetime.now().strftime("%H:%M:%S")
    line = RULE * max(0, width() - len(stamp) - 1)

    print(f"\n{DIM}{line} {stamp}{OFF}")
    print(f"{BOLD}{HAPPY:<{LABEL}}{OFF}{text}")


def note(text):
    print(f"{DIM}{text}{OFF}")
