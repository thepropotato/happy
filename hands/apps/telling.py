"""SHOW OR READ, DECIDED IN THREE MILLISECONDS, AND HOW SURE IT IS."""

import threading

import numpy as np

from hands.apps.wanting import READ, SHOW

# HOW FAR APART THE TWO SIMILARITIES HAVE TO BE BEFORE THIS ANSWERS BY ITSELF. UNDER IT THE
# QUESTION GOES TO THE MODEL INSTEAD, WHICH IS SLOW BUT UNDERSTANDS WORDS IT HAS NEVER SEEN.
# MEASURED: 0.05 CATCHES NINE OF THIRTEEN MISTAKES AND SENDS ONE IN SIX QUESTIONS ONWARD.
SURE = 0.05

learned = None

lock = threading.Lock()


def told(said):
    """SHOW, READ, OR None WHEN THIS IS TOO CLOSE TO CALL AND SOMETHING SLOWER SHOULD."""
    asked = str(said or "").strip()

    if not asked:
        return None

    try:
        towards, away = middles()

        from memory.embedding import vector

        point = vector(asked)
    except Exception:
        # NO EMBEDDING MODEL IS NOT AN ANSWER OF NO. THE SLOWER JUDGE STILL GETS ITS TURN.
        return None

    gap = float(point @ towards - point @ away)

    if abs(gap) < SURE:
        return None

    return SHOWN if gap > 0 else READING


SHOWN = "show"

READING = "read"


def middles():
    """THE MIDDLE OF EVERYTHING SAID TO BE SHOWN, AND THE MIDDLE OF EVERYTHING TO BE READ."""
    global learned

    if learned is None:
        with lock:
            if learned is None:
                learned = (centre(SHOW), centre(READ))

    return learned


def centre(lines):
    """ONE VECTOR FOR A WHOLE LIST: THE AVERAGE OF THEM, BACK ON THE UNIT SPHERE."""
    from memory.embedding import vector

    points = np.array([vector(each) for each in lines], dtype=np.float32)
    middle = points.mean(axis=0)

    return middle / np.linalg.norm(middle)


def warm():
    """WORK THE TWO MIDDLES OUT NOW, ON A THREAD, SO THE FIRST REAL QUESTION IS THREE MILLISECONDS."""
    threading.Thread(target=ready, daemon=True).start()


def ready():
    """WHAT THE THREAD RUNS. A MODEL THAT WILL NOT COME IS NOT WORTH SAYING TWICE."""
    try:
        middles()
    except Exception:
        pass


def forget():
    """DROP THE MIDDLES, FOR WHEN THE LINES BEHIND THEM CHANGE."""
    global learned

    learned = None
