"""SPEECH INTO TEXT, LOCALLY, WITH WHISPER."""

import numpy as np

from ears.engines import EarsError
from ears.languages import complete, download, picked
from ears.nonsense import clean
from face import show
from memory import settings

RATE = 16000

# CPU IS THE SAFE BASELINE EVERYWHERE.
PROVIDERS = {"cpu": ["CPUExecutionProvider"]}

# THE ONE LANGUAGE HAPPY HEARS. TOLD WHAT IT IS LISTENING TO, WHISPER NEVER SPENDS A PASS
# GUESSING, AND NEVER GUESSES WRONG.
ENGLISH = "en"


def missing(path):
    return f"No speech model in {path}. Get it with:\n  python -m ears --get"
model = None
built = None
cached = {}


def wanted():
    return settings.get("ears.device")


def whole():
    return complete(picked())


def load_model():
    """CALLED AT STARTUP, AND AGAIN WHEN A SETTING PICKS A DIFFERENT DEVICE."""
    global model, built, cached

    asked = wanted()
    choice = picked()
    state = (asked, choice["name"], str(choice["path"]), choice["quantization"])

    if state in cached:
        model = cached[state]
        built = state
        return model

    if not complete(choice):
        raise EarsError(missing(choice["path"]))

    import onnx_asr

    try:
        model = onnx_asr.load_model(
            choice["name"],
            choice["path"],
            quantization=choice["quantization"],
            providers=PROVIDERS.get(asked),
        )

        cached[state] = model
        built = state
    except Exception as error:
        if model is None:
            raise

        show.trouble(f"{asked} would not load, still hearing on {built} ({error})")

    return model


def transcribe(audio_file):
    """THE MODEL, TOLD WHAT IT IS LISTENING TO."""
    try:
        return clean(load_model().recognize(str(audio_file), language=ENGLISH))
    except Exception as error:
        show.trouble(f"This one would not be heard ({error})")
        return ""


def warm():
    """RECOGNISE ONCE NOW. THE FIRST CALL IS THE ONE THAT BUILDS THE SESSION."""
    load_model().recognize(np.zeros(RATE // 2, dtype=np.float32), sample_rate=RATE)


def fetch():
    """THE WEIGHTS. ONLY EVER RUN BY HAND, OR ONCE AT STARTUP."""
    return download()
