"""WHAT THE TERMINAL SHOWS. ONE BLOCK PER TURN, AND WHERE THE TIME WENT.

TIMES ARE MEASURED, NOT ESTIMATED. TOOLS REPORT THEMSELVES THROUGH step(), SO A
TOOL ADDED LATER APPEARS HERE WITHOUT ANYONE WIRING IT UP.
"""

import shutil
from datetime import datetime

from face.turn import MODEL, STARTED, Turn, stats

WIDTH = 78
RULE = "─"

YOU = "you"
HAPPY = "happy"

DIM = "\033[2m"
BOLD = "\033[1m"
OFF = "\033[0m"

LABEL = 6  # "happy " AND "you   " LINE UP.

turn = None


def width():
    return min(shutil.get_terminal_size((WIDTH, 24)).columns, WIDTH)


def wipe():
    print("\r" + " " * width() + "\r", end="")


def rule():
    stamp = datetime.now().strftime("%H:%M:%S")

    print(f"\n{DIM}{RULE * max(0, width() - len(stamp) - 1)} {stamp}{OFF}")


def begin():
    global turn

    turn = Turn()

    wipe()
    rule()


def listening():
    print(f"{DIM}{'':<{LABEL}}listening{OFF}", end="\r", flush=True)


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


def step(kind, name, seconds, about=None):
    """WHAT brain.watches() FEEDS. NO TOOL HAS TO KNOW THIS EXISTS.

    THE TERMINAL PRINTS ONE ACCOUNT AT THE END OF A TURN AND NOT A ROW PER CALL,
    SO WHAT about CARRIES GOES NOWHERE HERE.
    """
    if turn is None:
        return

    # A CALL THAT HAS MERELY STARTED CARRIES NO TIME AND MUST NOT BE ADDED UP.
    if kind == STARTED:
        return

    if kind == MODEL:
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


def unprompted(text):
    """WORK THAT FINISHED ON ITS OWN GETS ITS OWN BLOCK, NOT SOMEONE ELSE'S."""
    stamp = datetime.now().strftime("%H:%M:%S")
    line = RULE * max(0, width() - len(stamp) - 1)

    print(f"\n{DIM}{line} {stamp}{OFF}")
    print(f"{BOLD}{HAPPY:<{LABEL}}{OFF}{text}")


def note(text):
    print(f"{DIM}{text}{OFF}")
