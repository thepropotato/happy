"""EVERY GUARD AND EVERY JUDGEMENT, CALLED ONCE: python3 bench/reaching_guards.py

NO MODEL RUNS HERE AND NOTHING IS SCORED. THIS ONLY ASKS WHETHER EACH ONE STILL *RUNS* —
WHICH SOUNDS TOO CHEAP TO BE WORTH A FILE UNTIL brain/wrapping.py IS SPLIT UP AND THREE
FUNCTIONS QUIETLY LOSE A NAME THEY WERE READING OFF THE OLD MODULE. AN import CATCHES NONE
OF THOSE: THE NAME IS ONLY LOOKED UP WHEN THE LINE RUNS, AND THE LINE ONLY RUNS ON THE
EVENING THE GUARD IS NEEDED. bench/guarding.py SCORES THE JUDGEMENTS; THIS ONE WALKS THEM."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bench import sandbox

DB = sandbox.throwaway("reaching-guards.db")

from brain import guarding, malformed, repeats, sourcing, staleness, words, wrapping

# THE WORDS EACH REPLY GUARD IS HANDED. ONE OF THEM TRIPS EACH GUARD AND THE REST DO NOT,
# WHICH IS WHAT WALKS BOTH SIDES OF EVERY BRANCH.
SAYINGS = (
    "I've sent it.",
    "",
    "let me pull that up",
    "sorry, I can't do that",
    "click the first link",
    "you're watching Breaking Bad",
    "I can't create a presentation",
    "Yes, four chats are unread.",
)

# EVERY JUDGEMENT THE GUARDS LEAN ON, WITH ARGUMENTS THAT ARE MERELY THE RIGHT SHAPE.
JUDGEMENTS = (
    (staleness.stale_answer, ([], "any unread messages")),
    (staleness.stale_moving, ([],)),
    (staleness.about, ("any unread messages",)),
    (staleness.instructing, ("send jane a note",)),
    (staleness.moving, ("whatsapp_get_unread_messages",)),
    (words.asked_fresh, ("any unread messages",)),
    (words.disowning, ("i can't create a presentation",)),
    (words.unbacked, ("i've opened it", ["read_file"])),
    (malformed.unparsed, ("error parsing tool call",)),
    (malformed.telling, ("error parsing tool call",)),
    (malformed.minted, ()),
    (repeats.gist, ({"query": "the latest thing"},)),
    (repeats.learned, ()),
    (repeats.signature, ("read_file", {"path": "a"})),
    (repeats.repeated, ("read_file", {"path": "a"})),
    (repeats.repeated, ("open_url", {"url": "1"})),
    (repeats.circling, ("search_web", {"query": "a thing or other"})),
    (repeats.circling, ("search_web", {"query": "a"})),
    (repeats.remember, ("read_file", {"path": "a"}, "some answer")),
    (sourcing.checked, ("read_file", {"path": "x"})),
    (sourcing.checked, ("whatsapp_send_media_message", {"source": "/nope/made-up.pdf"})),
    (wrapping.announced, ("let me do it",)),
    (wrapping.unfinished, ()),
    (wrapping.held, ("any unread messages",)),
)


def walked():
    wrapping.fresh()
    wrong = 0

    # A JUDGEMENT WITH NOTHING BEHIND IT TAKES THE FIRST WAY OUT AND NEVER REACHES THE LINES
    # THAT READ A NAME. THE TURN IS GIVEN A CALL AND A REFUSAL FIRST SO BOTH SIDES RUN —
    # WITHOUT THIS, repeats.repeated LOOKED FINE HERE AND DIED ON A REAL EVENING OVER A NAME
    # THAT HAD MOVED TO ANOTHER MODULE.
    repeats.remember("open_url", {"url": "1"}, 'call this again with because="show"')
    repeats.remember("search_web", {"query": "a thing"}, "some answer")
    wrapping.ran.append("read_file")
    wrapping.refused["open_url"] = f"nothing yet. {wrapping.CARRY_ON}"
    wrapping.file_was_cut = True
    wrapping.file_cut_resume = 4000

    for guard in guarding.REPLY_GUARDS:
        for said in SAYINGS:
            try:
                guard(said, []) if guard is guarding.stale else guard(said)
            except Exception as error:
                wrong += 1
                print(f"✗ {guard.__name__}({said!r}) {type(error).__name__}: {error}")

    for judge, args in JUDGEMENTS:
        try:
            judge(*args)
        except Exception as error:
            wrong += 1
            print(f"✗ {judge.__module__}.{judge.__name__} {type(error).__name__}: {error}")

    total = len(guarding.REPLY_GUARDS) * len(SAYINGS) + len(JUDGEMENTS)
    print(f"{total - wrong}/{total} ran")

    return wrong


raise SystemExit(walked())
