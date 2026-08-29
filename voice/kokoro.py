"""THE SMOOTH VOICE: A SENTENCE AND A STYLE IN, SOUND OUT."""

import json

import numpy as np

import tongue
from bones import systems
from memory import settings
from voice import engines, phonemes
from voice.clips import resampled, tidied
from voice.engines import ELSEWHERE, VoiceError
from voice.styles import GET_THEM, MODEL, STYLES, VOCAB, find, whole

# THE REST OF THE ENGINE'S SURFACE, WHICH IS ABOUT THE FILES RATHER THAN THE MODEL.
from voice.styles import fetch, holds, installed, language  # noqa: F401

RATE = 24000

# THE MODEL AND ITS ALPHABET, AND THE VOICES FOR LANGUAGES IT CANNOT SAY, BUILT ON FIRST ASK.
loaded = None

borrowed = {}


class Voice:
    """SENTENCES IN, SOUND OUT. THE ONLY PART THAT KNOWS WHAT A MODEL IS."""

    rate = RATE

    def __init__(self, name=None, pace=None):
        self.pinned = name  # HANDED A NAME MEANS THE SETTING NEVER MOVES IT.
        self.held = pace  # AND A PACE THE SAME, WHICH refit MUST NOT READ BACK OVER.
        self.session, self.vocab = weights()

        self.load(name or find(), pace)

    def load(self, name, pace=None):
        self.style = np.fromfile(STYLES / f"{name}.bin", dtype=np.float32).reshape(-1, 1, 256)
        self.name = name
        self.pace = settings.get("voice.pace") if pace is None else pace

    def refit(self, text=""):
        """PICK UP A CHANGED VOICE OR PACE. A STYLE IS HALF A MEGABYTE, SO THIS COSTS NOTHING."""
        wanted = self.pinned or find(text)

        if self.held is not None:
            if wanted != self.name:
                self.load(wanted, self.held)

            return

        if wanted != self.name or settings.get("voice.pace") != self.pace:
            self.load(wanted)

    def say(self, text):
        parts = list(self.stream(text))

        return np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)

    def stream(self, text):
        """ONE SENTENCE AS THE PIECES IT IS MADE OF, EACH HANDED OVER THE MOMENT IT EXISTS
        RATHER THAN WHEN THE WHOLE SENTENCE IS DONE, WHICH IS WHAT THE WAIT BEFORE THE FIRST
        WORD USED TO BE."""
        spoken = tongue.reading(text)
        other = elsewhere(spoken)

        if other:
            for part in other.stream(text):
                yield resampled(part, other.rate, RATE)

            return

        self.refit(text)
        said = phonemes.spoken(text, spoken, self.vocab)
        last = len(said) - 1

        for at, mouthful in enumerate(said):
            yield tidied([self.sound(mouthful)], RATE, tail=at == last)

    def sound(self, said):
        """ONE MOUTHFUL OF SOUNDS THROUGH THE MODEL. THE STYLE IS PICKED BY HOW MANY THERE ARE."""
        marks = phonemes.ids(said, self.vocab)
        style = self.style[min(len(marks) - 2, len(self.style) - 1)]

        return self.session.run(
            None,
            {
                "input_ids": [marks],
                "style": style.astype(np.float32),
                # THE MODEL COUNTS SPEED UP WHERE THE SETTING COUNTS THE LENGTH OF A WORD DOWN.
                "speed": np.array([1.0 / (self.pace or 1.0)], dtype=np.float32),
            },
        )[0][0]

    def warm(self):
        """SYNTHESISE ONCE NOW. THE FIRST CALL COSTS MANY TIMES THE REST."""
        self.say("Ready.")


def pinned(name):
    """ONE STYLE BY NAME, WHICH NO SETTING AND NO SENTENCE CAN MOVE."""
    return Voice(name=name)


def weights():
    """ONE MODEL AND ONE ALPHABET FOR EVERY VOICE, READ OFF THE DISK ONCE PER RUN. LOADING IT
    AGAIN COSTS A THIRD OF A SECOND, AND ONNXRUNTIME RUNS ONE SESSION FROM ANY THREAD."""
    global loaded

    if loaded:
        return loaded

    import onnxruntime

    if not whole():
        raise VoiceError(GET_THEM)

    # LEFT TO ITSELF ONNXRUNTIME TAKES EVERY CORE THE MACHINE HAS, WHICH ON THIS ONE IS SLOWER
    # THAN TAKING THE FAST ONES AND ERRATIC ENOUGH THAT THE SAME SENTENCE VARIES THREEFOLD.
    options = onnxruntime.SessionOptions()
    options.intra_op_num_threads = systems.cores()

    vocab = json.loads(VOCAB.read_text(encoding="utf-8"))
    session = onnxruntime.InferenceSession(
        str(MODEL), options, providers=["CPUExecutionProvider"]
    )
    loaded = (session, vocab)

    return loaded


def elsewhere(spoken):
    """THE VOICE FOR A LANGUAGE THIS MODEL CANNOT SAY, BUILT THE FIRST TIME IT IS ASKED FOR."""
    if spoken not in ELSEWHERE:
        return None

    if spoken not in borrowed:
        borrowed[spoken] = engines.part(ELSEWHERE[spoken]).Voice()

    return borrowed[spoken]
