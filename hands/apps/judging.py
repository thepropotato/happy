"""ASKING A SECOND TIME WHETHER A PAGE REALLY BELONGS ON THEIR SCREEN."""

import threading

from hands.apps import telling

# THE WHOLE PROMPT. IT IS SHORT ON PURPOSE, AND NOT ONLY BECAUSE THE BIG ONE IS WHAT THE
# MODEL IS ALREADY GETTING THIS WRONG UNDER: EVERY SENTENCE HERE IS ONE MORE THING FOR A
# REASONING MODEL TO WEIGH OUT LOUD BEFORE IT ANSWERS, AND THAT IS THE WHOLE COST.
ASKED = """Someone said: {said}

Did they ask to see a page, or ask a question? Answer with one word, SHOW or READ."""

SHOW = "SHOW"

READ = "READ"

# A JUDGE THAT CANNOT MAKE ITS MIND UP LETS THE PAGE THROUGH. A SWALLOWED "SHOW ME" IS A
# WORSE FAILURE THAN THE ONE BEING FIXED, BECAUSE IT LOOKS LIKE HAPPY IGNORING THEM.
UNSURE = SHOW

# BUILT ONCE. THE JUDGE RUNS ON EVERY OPEN AND REBUILDING IT EACH TIME WOULD COST MORE
# THAN THE THING IT IS GUARDING.
held = None

lock = threading.Lock()


def wanted(said):
    """WHETHER THIS PAGE BELONGS ON THEIR SCREEN. TRUE UNLESS SOMETHING IS SURE IT DOES NOT."""
    if not said:
        return True

    # THREE MILLISECONDS FIRST. IT ANSWERS FIVE TIMES IN SIX, AND HANDS THE CLOSE ONES ON TO
    # THE MODEL, WHICH TAKES NEARLY THREE SECONDS BUT UNDERSTANDS WORDS IT HAS NEVER SEEN.
    quick = telling.told(said)

    if quick is not None:
        return quick == telling.SHOWN

    return asked(said) != READ


def asked(said):
    """THE JUDGE'S ONE WORD, OR WHAT WE DO WHEN IT WILL NOT SAY ONE."""
    try:
        answer = judge().invoke(ASKED.format(said=said))
    except Exception:
        # A JUDGE THAT IS DOWN NEVER STOPS A PAGE. THE TOOL BEHAVES AS IT ALWAYS DID.
        return UNSURE

    return worded(answer)


def worded(answer):
    """SHOW OR READ OUT OF WHATEVER THE MODEL ACTUALLY SAID."""
    # .content IS THE PLAIN FIELD AND IS NEVER THE DEPRECATED CALLABLE .text IS ON SOME
    # BACKENDS. ONE WORD IS ALL THIS ASKED FOR, SO A LIST OF PARTS IS FLATTENED THE BLUNT WAY.
    said = getattr(answer, "content", None)

    if not isinstance(said, str):
        said = str(said or "")

    said = said.strip().upper()

    if READ in said and SHOW not in said:
        return READ

    if SHOW in said:
        return SHOW

    return UNSURE


def judge():
    """THE SMALL MODEL BEHIND THE QUESTION, BUILT ONCE AND KEPT."""
    global held

    if held is None:
        with lock:
            if held is None:
                from brain import model  # LATE: brain REACHES BACK INTO hands.

                held = model.create()

    return held


def forget():
    """DROP THE HELD MODEL, FOR WHEN THE SETTINGS BEHIND IT MOVE."""
    global held

    held = None
