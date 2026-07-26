"""
WHAT THE TERMINAL SHOWS. ONE BLOCK PER TURN, AND WHERE THE TIME WENT.

A VOICE ASSISTANT SPENDS MOST OF A TURN DOING NOTHING VISIBLE, SO WHEN IT FEELS
SLOW THERE IS NO WAY TO TELL WHICH PART WAS SLOW. THE STATS LINE IS THERE TO
ANSWER THAT WITHOUT A PROFILER: HEARING, THINKING, EACH TOOL BY NAME, AND HOW
LONG UNTIL THE FIRST WORD CAME OUT, WHICH IS THE ONLY LATENCY A PERSON FEELS.

TIMES ARE MEASURED, NOT ESTIMATED. TOOLS REPORT THEMSELVES FROM THE MIDDLEWARE
IN brain.py, SO A TOOL ADDED LATER APPEARS HERE WITHOUT ANYONE WIRING IT UP.

ONE TURN IS LIVE AT A TIME AND IT LIVES IN A MODULE LEVEL Turn, THE SAME WAY
chat.py TAKES MESSAGES. THE ALTERNATIVE IS THREADING A COLLECTOR THROUGH EVERY
CALL FOR THE SAKE OF PRINTING.
"""

import shutil
import time
from datetime import datetime

WIDTH = 78
RULE = "─"
BAR = "│"
DOT = "·"

YOU = "you"
HAPPY = "happy"

# DIM FOR ANYTHING THAT IS NOT WHAT WAS SAID. THE STATS MATTER LESS THAN THE
# WORDS AND SHOULD NOT COMPETE WITH THEM FOR ATTENTION.
DIM = "\033[2m"
BOLD = "\033[1m"
OFF = "\033[0m"

LABEL = 6  # "happy " AND "you   " LINE UP, SO THE WORDS START IN ONE COLUMN.

turn = None


class Turn:
    """ONE EXCHANGE, AND A STOPWATCH ON EACH PART OF IT."""

    def __init__(self):
        self.started = time.perf_counter()
        self.heard = None
        self.first = None
        self.thought = None
        self.tools = []
        self.speaking = False

    def seconds(self):
        return time.perf_counter() - self.started

    def add(self, name, taken):
        self.tools.append((name, taken))

    def spent(self):
        return sum(taken for _, taken in self.tools)


def width():
    return min(shutil.get_terminal_size((WIDTH, 24)).columns, WIDTH)


def wipe():
    """CLEAR THE LINE THE LISTENING INDICATOR LEFT SITTING THERE."""
    print("\r" + " " * width() + "\r", end="")


def rule():
    stamp = datetime.now().strftime("%H:%M:%S")

    print(f"\n{DIM}{RULE * max(0, width() - len(stamp) - 1)} {stamp}{OFF}")


def begin():
    """A NEW TURN. THE RULE IS THE SEGREGATION BETWEEN ONE AND THE NEXT."""
    global turn

    turn = Turn()

    wipe()
    rule()


def listening():
    print(f"{DIM}{'':<{LABEL}}listening{OFF}", end="\r", flush=True)


def said(text, seconds=None):
    """WHAT WAS HEARD, ONCE IT IS KNOWN."""
    if turn:
        turn.heard = seconds

    print(f"{BOLD}{YOU:<{LABEL}}{OFF}{text}")


def opening():
    """THE START OF HAPPY'S LINE, BEFORE ANY OF IT HAS ARRIVED."""
    if turn:
        turn.speaking = True

    print(f"{BOLD}{HAPPY:<{LABEL}}{OFF}", end="", flush=True)


def piece(text):
    """ONE PIECE OF THE REPLY, AS IT ARRIVES. THE FIRST ONE STOPS A STOPWATCH."""
    if turn and turn.first is None:
        turn.first = turn.seconds()

    print(text, end="", flush=True)


MODEL = "model"


def step(kind, name, seconds):
    """WHAT brain.watches() FEEDS. NO TOOL HAS TO KNOW THIS EXISTS."""
    if turn is None:
        return

    if kind == MODEL:
        turn.thought = seconds
    else:
        turn.add(name, seconds)


def trouble(text):
    print(f"\n{DIM}{'':<{LABEL}}{text}{OFF}")


def end():
    """CLOSE THE TURN WITH WHERE THE TIME WENT."""
    if turn is None:
        return

    if turn.speaking:
        print()

    for line in stats(turn):
        print(f"{DIM}{'':<{LABEL}}{line}{OFF}")


def stats(this):
    """ONE OR TWO DIM LINES. TOOLS GET THEIR OWN, BECAUSE THEY ARE THE SURPRISE."""
    parts = []

    if this.heard is not None:
        parts.append(f"heard {clock(this.heard)}")

    if this.thought is not None:
        # THE MODEL'S OWN TIME, WITH THE WAITING ON TOOLS TAKEN BACK OUT, OR THE
        # TWO NUMBERS WOULD DOUBLE COUNT AND NEITHER WOULD MEAN ANYTHING.
        parts.append(f"thought {clock(max(0.0, this.thought - this.spent()))}")

    if this.tools:
        parts.append(f"tools {clock(this.spent())}")

    if this.first is not None:
        parts.append(f"first word {clock(this.first)}")

    parts.append(f"total {clock(this.seconds())}")

    lines = [f" {BAR} ".join(parts)]

    if this.tools:
        each = f" {DOT} ".join(f"{name} {clock(taken)}" for name, taken in this.tools)
        lines.append(f"{DOT} {each}")

    return lines


def clock(seconds):
    return f"{seconds * 1000:.0f}ms" if seconds < 1 else f"{seconds:.2f}s"


def unprompted(text):
    """WORK THAT FINISHED ON ITS OWN GETS ITS OWN BLOCK, NOT SOMEONE ELSE'S."""
    clock_now = datetime.now().strftime("%H:%M:%S")
    line = RULE * max(0, width() - len(clock_now) - 1)

    print(f"\n{DIM}{line} {clock_now}{OFF}")
    print(f"{BOLD}{HAPPY:<{LABEL}}{OFF}{text}")


def note(text):
    print(f"{DIM}{text}{OFF}")
