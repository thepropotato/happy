"""AN EVEN PACE: THE MODEL PICKS ONE LENGTH FOR A WHOLE SENTENCE AND FITS THE WORDS INTO IT, AND THAT
PICK WANDERS BY HALF EITHER WAY, SO IT IS READ FIRST AND THE SPEED SET SO EVERY SENTENCE LANDS THE SAME."""

import re

import numpy as np

# LETTERS A SECOND AT PACE ONE. MEASURED OFF SIXTY OF HAPPY'S OWN SENTENCES: TWELVE IS ABOUT A
# HUNDRED AND SEVENTY WORDS A MINUTE, WHICH IS HOW A PERSON TALKS TO SOMEBODY IN THE ROOM.
LETTERS_PER_SECOND = 12.0

# THE ROOM THE MODEL LEAVES AROUND AN UTTERANCE, IN SECONDS, MEASURED AT 1.10 GIVE OR TAKE 0.17.
# IT IS INSIDE THE PREDICTED LENGTH AND TRIMMED OFF AFTERWARDS, SO IT IS NOT SPEECH.
PADDING = 1.1

# WHAT THE MODEL ACCEPTS. PAST EITHER END IT GARBLES RATHER THAN HURRIES.
SLOWEST = 0.7
FASTEST = 1.6

# UNDER THIS MANY LETTERS THE PREDICTION IS MOSTLY PADDING, SO THE MODEL'S OWN PACE IS KEPT.
FEW = 6

LETTERS = re.compile(r"[A-Za-z]")


def speed(engine, style, text, pace):
    """THE SPEED THAT SAYS text AT THE SET PACE, FROM THE MODEL'S OWN LENGTH PREDICTION."""
    letters = len(LETTERS.findall(text))

    if letters < FEW:
        return 1.0 / (pace or 1.0)

    predicted = seconds(engine, style, text)

    if predicted is None:
        return 1.0 / (pace or 1.0)

    speaking = max(predicted - PADDING, 0.05)
    wanted = letters / LETTERS_PER_SECOND * (pace or 1.0)

    return float(np.clip(speaking / wanted, SLOWEST, FASTEST))


def wanted(text, pace):
    """HOW LONG text SHOULD TAKE TO SAY AT THIS PACE, IN SECONDS OF ACTUAL SPEECH."""
    return len(LETTERS.findall(text)) / LETTERS_PER_SECOND * (pace or 1.0)


def off(spoken_seconds, text, pace):
    """HOW FAR A CLIP LANDED FROM THE PACE: 1.0 IS ON IT, 1.3 IS THIRTY PERCENT TOO FAST."""
    target = wanted(text, pace)

    if target <= 0 or spoken_seconds <= 0:
        return 1.0

    return target / spoken_seconds


def corrected(speed_used, drift):
    """THE SPEED TO TRY AGAIN WITH, ONCE, WHEN THE FIRST GO LANDED TOO FAR OUT."""
    return float(np.clip(speed_used / drift, SLOWEST, FASTEST))


# A CLIP THIS FAR OFF THE PACE IS HEARD AS A BLURT OR A DRAWL, AND IS WORTH A SECOND GO.
TOLERANCE = 0.2


def seconds(engine, style, text):
    """HOW LONG THE MODEL MEANS TO TAKE OVER text AT SPEED ONE, OR None IF IT WILL NOT SAY."""
    try:
        ids, mask = engine.text_processor([text], "en")
        duration, *_ = engine.dp_ort.run(
            None, {"text_ids": ids, "style_dp": style.dp, "text_mask": mask}
        )

        return float(duration[0])
    except Exception:
        return None
