"""SHOW OR READ, DECIDED IN THREE MILLISECONDS, AND HOW SURE IT IS."""

import threading

import numpy as np

from hands.apps.wanting import READ, SHOW

# HOW FAR APART THE TWO SIMILARITIES HAVE TO BE BEFORE THIS ANSWERS BY ITSELF. UNDER IT THE
# QUESTION GOES TO THE MODEL INSTEAD, WHICH IS SLOW BUT UNDERSTANDS WORDS IT HAS NEVER SEEN.
# NEAREST NEIGHBOUR SPREADS THE TWO SIDES MUCH FURTHER APART THAN THE AVERAGE DID, SO THE
# GAP THAT MEANS "SURE" IS WIDER TOO. MEASURED OVER THE LINES BELOW AND THE MISTAKES THAT
# PROMPTED THEM: 0.15 IS RIGHT ON 17 OF 18 AND HANDS ON THE ONE IT IS NOT SURE OF.
SURE = 0.15

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

    # THE NEAREST LINE ON EACH SIDE, NOT THE MIDDLE OF EITHER. "SHOW ME THE LINK" AND "SHOW ME
    # THE VIDEO" SIT ALMOST ON TOP OF EACH OTHER, AND AVERAGING EVERY LINE INTO ONE POINT
    # RUBBED OUT THE VERY DIFFERENCE BEING ASKED ABOUT: BOTH CAME OUT "SHOW" BY A HAIR.
    gap = float((towards @ point).max() - (away @ point).max())

    if abs(gap) < SURE:
        return None

    return SHOWN if gap > 0 else READING


SHOWN = "show"

READING = "read"


def middles():
    """EVERY LINE SAID TO BE SHOWN, AND EVERY LINE TO BE READ, EACH AS A POINT OF ITS OWN."""
    global learned

    if learned is None:
        with lock:
            if learned is None:
                learned = (points(SHOW), points(READ))

    return learned


def points(lines):
    """ONE VECTOR PER LINE, KEPT APART RATHER THAN AVERAGED INTO ONE."""
    from memory.embedding import vector

    return np.array([vector(each) for each in lines], dtype=np.float32)


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
