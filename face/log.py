"""THE FACE THAT WRITES IT ALL DOWN: data/happy.log.

THE TERMINAL SAYS WHAT HAPPY IS DOING AND THEN IT IS GONE, AND THE WINDOW NEVER
HAD A TERMINAL TO SAY IT TO. THIS IS THE SAME ACCOUNT, KEPT: ONE STAMPED LINE PER
THING THAT HAPPENED, IN THE ORDER IT HAPPENED, WHICH IS WHAT A LOG IS.

IT IS A FACE LIKE THE OTHER TWO AND HEARS EXACTLY WHAT THEY HEAR, SO NOTHING
ANYWHERE HAS TO REMEMBER TO LOG. WHAT IS LEFT OUT IS THE LIVE PART — HOW LOUD THE
ROOM IS, WHICH MOOD THE ORB IS IN — BECAUSE NONE OF IT IS AN EVENT AND ALL OF IT
ARRIVES TEN TIMES A SECOND.

EVERY LINE IS ONE LINE. A REPLY WITH NEWLINES IN IT IS FLATTENED ON THE WAY IN,
BECAUSE A LOG WHERE ONE EVENT CAN SPAN SIX LINES IS A LOG NOTHING CAN GREP.
"""

import threading
from datetime import datetime
from pathlib import Path

from face.turn import MODEL, SPENT, STARTED, Turn, count, stats

FILE = Path(__file__).resolve().parents[1] / "data" / "happy.log"

# ONE ROTATION AND NO MORE. THE OLD ONE IS THERE FOR THE MORNING AFTER A CRASH,
# AND NOBODY HAS EVER GONE LOOKING FOR THE ONE BEFORE THAT.
MOST_BYTES = 2_000_000

OLDER = ".1"

WIDE = 7  # THE KIND COLUMN, SO EVERY LINE'S WORDS START IN THE SAME PLACE.

turn = None
reply = ""

writing = threading.Lock()
handle = None


def opened(how):
    """START A RUN'S WORTH OF LOG. how IS WHAT IS RUNNING, FOR THE FIRST LINE."""
    global handle

    FILE.parent.mkdir(parents=True, exist_ok=True)
    rotate()

    with writing:
        handle = FILE.open("a", buffering=1, encoding="utf-8")

    line("run", f"happy started, {how}, {datetime.now().astimezone():%d %b %Y}")


def closed(why="stopped"):
    global handle

    line("run", f"happy {why}")

    with writing:
        if handle is not None:
            handle.close()
            handle = None


def rotate():
    """A LOG BIG ENOUGH TO BE SLOW TO OPEN IS PUT ASIDE, NOT TRIMMED IN PLACE."""
    try:
        if FILE.exists() and FILE.stat().st_size > MOST_BYTES:
            FILE.replace(FILE.with_suffix(FILE.suffix + OLDER))
    except OSError:
        pass


def line(kind, text):
    """ONE EVENT. NEVER RAISES: A LOG THAT CAN STOP HAPPY IS WORSE THAN NO LOG."""
    said = " ".join(str(text).split())

    if not said:
        return

    stamp = f"{datetime.now():%H:%M:%S.%f}"[:-3]

    with writing:
        if handle is None:
            return

        try:
            handle.write(f"{stamp}  {kind:<{WIDE}}{said}\n")
        except Exception:
            pass


# ── THE FACE ITSELF ──


def note(text):
    line("note", text)


def trouble(text):
    line("error", text)


def begin():
    global turn, reply

    turn = Turn()
    reply = ""


def said(text, seconds=None):
    if turn:
        turn.heard = seconds

    line("you", text)


def piece(text):
    """THE REPLY ARRIVES A FEW LETTERS AT A TIME AND IS WRITTEN DOWN WHOLE, ONCE."""
    global reply

    if turn and turn.first is None:
        turn.first = turn.seconds()

    reply += text


def step(kind, name, seconds, about=None):
    """WHAT brain.watches() FEEDS: A CALL DONE, OR THE MODEL'S OWN THINKING TIME.

    ONE LINE PER CALL AND NOT TWO. A CALL THAT HAS ONLY STARTED CARRIES NEITHER
    ITS TIME NOR THE REASON IT WAS MADE, WHICH IS EVERYTHING WORTH WRITING DOWN,
    AND ONE THAT NEVER CAME BACK IS ALREADY A GAP IN THE STAMPS.
    """
    if turn is None or kind == STARTED:
        return

    if kind == SPENT:
        turn.paid(about)

        return

    if kind == MODEL:
        turn.thought = seconds

        return

    turn.add(name, seconds)

    why = (about or {}).get("why")

    # A CALL THAT WORKED AND FOUND NOTHING IS ITS OWN KIND OF LINE. IT IS NOT AN
    # ERROR AND IT IS NOT A RESULT, AND A ROW OF THEM IS WHAT GOING ROUND IN
    # CIRCLES LOOKS LIKE — WHICH IS ONLY VISIBLE IF THEY LOOK DIFFERENT.
    kind = "no" if (about or {}).get("failed") else "tool"

    # WHAT THE ROUND THAT ASKED FOR THIS CALL READ, WHICH IS THE STANDING PROMPT
    # AND EVERY TOOL SCHEMA OVER AGAIN. THE ONE NUMBER WORTH SEEING PER STEP.
    read = ((about or {}).get("spent") or {}).get("read")
    cost = f" {count(read)}" if read else ""

    line(kind, f"{name} {clock(seconds)}{cost}" + (f" — {why}" if why else ""))


def unprompted(text):
    line("happy", f"(unprompted) {text}")


def end():
    if turn is None:
        return

    if reply.strip():
        line("happy", reply)

    # ONLY THE FIRST LINE OF IT: THE SECOND IS EVERY CALL AND ITS TIME AGAIN, AND
    # EVERY CALL AND ITS TIME IS ALREADY A LINE OF ITS OWN UP ABOVE.
    line("spent", stats(turn)[0])


def clock(seconds):
    if seconds is None:
        return ""

    return f"{seconds * 1000:.0f}ms" if seconds < 1 else f"{seconds:.2f}s"


def lines():
    """THE WHOLE LOG BACK AGAIN, OLDEST FIRST, FOR SOMETHING THAT HAS TO SHOW IT."""
    try:
        return FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
