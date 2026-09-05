"""SOUND TIDIED AT ITS EDGES, SO ONE PIECE RUNS INTO THE NEXT WITHOUT A GAP OR A CLICK."""

import numpy as np

# ANYTHING THIS MUCH QUIETER THAN THE LOUDEST PART OF A CLIP IS ROOM, NOT SPEECH. AT TWO
# PERCENT THE SOFT END OF A WORD WENT WITH THE ROOM: MEASURED, "PURCHASE" LOST FIFTY MILLISECONDS.
FLOOR = 0.005

# WHAT IS LEFT EITHER SIDE OF THE SPEECH, SO A WORD DOES NOT START ALREADY UNDER WAY.
KEEP_MS = 40

# A CUT STRAIGHT THROUGH A WAVE IS HEARD AS A CLICK. THIS IS THE SHORTEST RAMP THAT HIDES ONE.
FADE_MS = 6

# THE BREATH AFTER A SENTENCE, BY WHAT ENDED IT. THE MODEL'S OWN PAUSE AT A FULL STOP INSIDE
# ONE UTTERANCE MEASURES 420 TO 580 MS AND AT A COMMA 140 TO 330, SO A FIXED 90 MS HERE MADE
# EVERY FULL STOP SHORTER THAN EVERY COMMA, WHICH IS HEARD AS A VOICE RUNNING ITS SENTENCES
# TOGETHER. A PIECE CUT OUT OF A LONGER SENTENCE AT A CLAUSE GETS A COMMA'S WORTH.
TAIL_MS = 450
CLAUSE_MS = 220
TAILS = {".": 450, "!": 480, "?": 480, ":": 320, ";": 320, ",": CLAUSE_MS}


def breath(text):
    """HOW LONG TO REST AFTER text, IN MILLISECONDS, READ OFF HOW IT ENDS."""
    said = (text or "").rstrip("\"')] ")

    return TAILS.get(said[-1:], CLAUSE_MS)


def tidied(parts, rate, tail=True):
    """SEVERAL MOUTHFULS OF ONE SENTENCE AS A SINGLE CLIP, WITH A BREATH AFTER IT. tail IS
    THE BREATH IN MILLISECONDS, True FOR A FULL STOP'S WORTH, False FOR NONE BECAUSE THE REST
    OF ITS OWN SENTENCE RUNS STRAIGHT INTO IT."""
    kept = [faded(trimmed(part, rate), rate) for part in parts if part is not None]
    kept = [part for part in kept if len(part)]

    if not kept:
        return np.zeros(0, dtype=np.float32)

    if tail is False or tail == 0:
        return np.concatenate(kept)

    return np.concatenate(kept + [quiet(TAIL_MS if tail is True else int(tail), rate)])


def trimmed(samples, rate):
    """THE SPEECH OUT OF A CLIP, WITHOUT THE ROOM EITHER SIDE OF IT."""
    loud = np.abs(samples)

    if not len(loud) or not loud.max():
        return samples[:0]

    speaking = np.flatnonzero(loud > loud.max() * FLOOR)

    if not speaking.size:
        return samples[:0]

    margin = span(KEEP_MS, rate)
    first = max(0, int(speaking[0]) - margin)
    last = min(len(samples), int(speaking[-1]) + 1 + margin)

    return samples[first:last]


def faded(samples, rate):
    """BOTH ENDS BROUGHT UP AND BACK DOWN FROM NOTHING."""
    ramp = min(span(FADE_MS, rate), len(samples) // 2)

    if ramp < 2:
        return samples

    edge = np.linspace(0.0, 1.0, ramp, dtype=np.float32)
    eased = samples.astype(np.float32, copy=True)

    eased[:ramp] *= edge
    eased[-ramp:] *= edge[::-1]

    return eased


def resampled(samples, was, now):
    """ONE CLIP AT ANOTHER RATE, DONE ON THE SPECTRUM RATHER THAN BY DRAWING LINES BETWEEN THE
    SAMPLES, WHICH FILTERS SO POORLY THAT THE TOP OF THE SPEECH COMES BACK MIRRORED AS CRACKLE."""
    if was == now or not len(samples):
        return samples

    count = round(len(samples) * now / was)

    if count < 2:
        return np.zeros(0, dtype=np.float32)

    spectrum = np.fft.rfft(samples)
    moved = np.zeros(count // 2 + 1, dtype=spectrum.dtype)
    kept = min(len(spectrum), len(moved))

    # WHAT THE NEW RATE CANNOT HOLD IS DROPPED HERE RATHER THAN FOLDED BACK OVER THE SPEECH.
    moved[:kept] = spectrum[:kept]

    return (np.fft.irfft(moved, count) * (count / len(samples))).astype(np.float32)


def quiet(milliseconds, rate):
    return np.zeros(span(milliseconds, rate), dtype=np.float32)


def span(milliseconds, rate):
    return int(rate * milliseconds / 1000)
