"""WHAT THE KNOWLEDGE BASE LEARNS AND WHAT IT REFUSES: python3 bench/knowing.py

TWO THINGS THE BENCH CANNOT ASK. A REPLAY MOCKS EVERY TOOL, SO THE CLIENT THAT SAVES A
CONFIRMED NAME NEVER RUNS THERE, AND THE PATHS IN A CANNED RESULT ARE NOT REAL FILES.
BOTH ARE CHECKED HERE INSTEAD, AGAINST A SCRATCH STORE THAT IS THROWN AWAY AFTER."""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SCRATCH = tempfile.mkdtemp(prefix="happy-memory-")

# BEFORE ANY HAPPY IMPORT AT ALL: memory.storage FIXES THE FILE AT IMPORT, AND THE memory
# PACKAGE ITSELF PULLS IT IN, SO THIS CANNOT LIVE INSIDE THAT PACKAGE. THE FACTS LIVE BESIDE
# THE DATABASE, SO POINTING THAT AWAY IS WHAT KEEPS A TEST OUT OF THE REAL HISTORY — AN
# EARLIER GO AT THIS LEFT ITS OWN MADE-UP CONTACT IN IT.
os.environ["HAPPY_DB"] = str(Path(SCRATCH) / "scratch.db")

from brain import sourcing
from hands.files import held
from memory import knowledge, storage

if Path(storage.path()).parent != Path(SCRATCH).resolve():
    raise SystemExit(f"refusing to run: the store is {storage.path()}, not the scratch one")

WHERE = "whatsapp"


def learning():
    """A NAME PUT TO THEM ON ONE TURN AND CONFIRMED ON THE NEXT IS LEARNED WITHOUT BEING ASKED.

    THIS IS THE WHOLE OF WHAT WENT WRONG WITH "SUSI": THE GUESS WAS QUEUED IN MEMORY ON A
    CLIENT THAT WAS THROWN AWAY WITH THE REQUEST, SO THE CONFIRMATION ARRIVED TO AN EMPTY
    DICT AND THE SAME QUESTION WAS ASKED THREE NIGHTS RUNNING."""
    rows, wrong = [], 0

    knowledge.expect("Suri", "Suripriya", WHERE)

    rows.append(("the guess is waiting", knowledge.awaiting("Suripriya", WHERE), "Suri"))
    rows.append(("nothing learned yet", knowledge.recall("Suri", WHERE), None))

    # THE NEXT TURN, WHICH IN A CONNECTOR IS A DIFFERENT PROCESS ENTIRELY: THE ONLY THING
    # CARRYING THE GUESS ACROSS IS THAT IT WAS WRITTEN DOWN.
    spoken = knowledge.awaiting("Suripriya", WHERE)

    if spoken:
        knowledge.remember_fact(spoken, WHERE, "Suripriya")
        knowledge.settle("Suripriya", WHERE)

    rows.append(("learned after the yes", knowledge.recall("Suri", WHERE), "Suripriya"))
    rows.append(("learned whatever the case", knowledge.recall("suri", WHERE), "Suripriya"))
    rows.append(("no longer waiting", knowledge.awaiting("Suripriya", WHERE), None))
    rows.append(("another service is its own", knowledge.recall("Suri", "gmail"), None))

    for said, got, want in rows:
        wrong += got != want
        print(f"{'✗' if got != want else ' '} {said:<28} {str(got):<14} {'' if got == want else f'want {want}'}")

    return wrong, len(rows)


def sourced():
    """A PATH MAY BE ACTED ON ONLY IF A TOOL HANDED IT OVER."""
    real = Path(SCRATCH) / "Some Person Offer Letter.pdf"
    real.write_text("x", encoding="utf-8")

    held.given.clear()
    held.offer(str(real))

    made_up = str(Path(SCRATCH) / "offer_letter.pdf")
    sending = "whatsapp_send_media_message"

    rows = [
        ("a path that was listed", sending, {"source": str(real)}, False),
        ("a path it wrote itself", sending, {"source": made_up}, True),
        ("the same, in a list", sending, {"source": [made_up]}, True),
        ("a bare name to look up", sending, {"source": "offer letter"}, False),
        ("an address, not a path", sending, {"source": "https://x.test/a.png"}, False),
        ("a file being made", "write_file", {"path": made_up}, False),
        ("a name read_file resolves", "read_file", {"path": made_up}, False),
    ]

    wrong = 0

    for said, name, args, want in rows:
        got = bool(sourcing.checked(name, args))
        wrong += got != want
        print(f"{'✗' if got != want else ' '} {said:<28} {'refused' if got else 'allowed':<14} "
              f"{'' if got == want else ('want refused' if want else 'want allowed')}")

    return wrong, len(rows)


def checked():
    wrong = total = 0

    for name, run in (("learning a name", learning), ("where a path came from", sourced)):
        print(f"\n{name}")
        missed, count = run()
        wrong += missed
        total += count

    print(f"\n{total - wrong}/{total}")

    return wrong


raise SystemExit(checked())
