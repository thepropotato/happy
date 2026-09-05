"""THE VOICE THAT BREATHES: A SENTENCE IN, SOUND OUT, WITH THE PAUSES WHERE THE WORDS PUT THEM."""

from pathlib import Path

import numpy as np

from bones import systems
from memory import settings
from voice.clips import breath, tidied
from voice.engines import VoiceError

RATE = 44100

MODELS = Path(__file__).resolve().parent.parent / "models" / "supertonic"
GRAPHS = MODELS / "onnx"
STYLES = MODELS / "voice_styles"

# EIGHT PASSES IS WHAT THE LIBRARY ASKS FOR AND FOUR IS WHERE IT STOPS GETTING BETTER: THE
# PAUSES AND THE PITCH ARE THE SAME AT FOUR AS AT EIGHT AND IT COSTS HALF THE WAIT. AT TWO
# THE SOUND CLIPS.
STEPS = 4

# THE TEN IT SHIPS WITH, THE MEN FIRST BECAUSE THE FIRST NAME HERE IS THE ONE THAT SPEAKS
# WHEN NOBODY HAS PICKED.
VOICES = ["M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5"]

DEFAULT = "M1"

# JUST UNDER ONE, SO A CLIP THAT WAS ALREADY LOUD IS NOT LEFT SITTING ON THE CEILING.
CEILING = 0.99

ENGLISH = "en"

GET_THEM = "No expressive voice on this machine. Get it with:\n  python -m voice --get --engine supertonic"

# THE MODEL AND THE STYLES IT HOLDS, BUILT ON FIRST ASK.
loaded = None


class Voice:
    """SENTENCES IN, SOUND OUT. THE ONLY PART THAT KNOWS WHAT A MODEL IS."""

    rate = RATE

    def __init__(self, name=None, pace=None):
        self.pinned = name  # HANDED A NAME MEANS THE SETTING NEVER MOVES IT.
        self.held = pace  # AND A PACE THE SAME, WHICH refit MUST NOT READ BACK OVER.
        self.speech = weights()

        self.load(name or find(), pace)

    def load(self, name, pace=None):
        self.style = self.speech.get_voice_style(voice_name=name)
        self.name = name
        self.pace = settings.get("voice.pace") if pace is None else pace

    def refit(self, text=""):
        """PICK UP A CHANGED VOICE OR PACE. A STYLE IS A HANDFUL OF NUMBERS OFF A MODEL ALREADY
        IN MEMORY, SO THIS COSTS NOTHING."""
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
        """ONE SENTENCE, WHOLE. THE MODEL SHAPES AN UTTERANCE AT ONCE AND HAS NOTHING TO HAND
        OVER UNTIL IT IS DONE, SO THE SENTENCE IS THE PIECE."""
        self.refit(text)

        # THE MODEL PADS EVERY UTTERANCE WITH ROOM AT BOTH ENDS, ABOUT A SECOND OF IT, WHICH
        # IS DEAD AIR BEFORE THE FIRST WORD AND AFTER THE LAST.
        yield tidied([self.sound(text)], self.rate, tail=breath(text))

    def sound(self, text):
        """ONE SENTENCE THROUGH THE MODEL, ONCE, AT THE SPEED THE PERSON SET.

        NOTHING MEASURES THE CLIP AFTERWARDS AND NOTHING MAKES IT TWICE. FITTING EVERY SENTENCE
        TO A LETTERS-PER-SECOND TARGET PINNED ORDINARY ONES TO THE SLOWEST SPEED THE MODEL TAKES
        AND STRETCHED HAPPY BY TWO THIRDS, WHICH IS HEARD AS A DRAWL. THE MODEL ALREADY VARIES
        ITS OWN PACE ACROSS A SENTENCE, AND THAT VARIATION IS WHAT MAKES IT SOUND LIKE A PERSON."""
        return self.once(text, 1.0 / (self.pace or 1.0))

    def once(self, text, speed):
        made = self.speech.synthesize(
            text, voice_style=self.style, lang=ENGLISH, total_steps=STEPS, speed=speed
        )

        # IT HANDS BACK THE SOUND AND HOW LONG IT RUNS, AND HAS SWAPPED THEIR ORDER BEFORE.
        for piece in made:
            if isinstance(piece, np.ndarray) and piece.size > 1:
                return levelled(piece.flatten().astype(np.float32))

        return np.zeros(0, dtype=np.float32)

    def warm(self):
        """SYNTHESISE ONCE NOW. THE FIRST CALL COSTS MANY TIMES THE REST."""
        self.say("Ready.")


def levelled(sound):
    """A CLIP BROUGHT UNDER THE CEILING WHOLE. THE MODEL OVERSHOOTS ONE ON SOME SENTENCES, AND
    CUTTING THE TOPS OFF IS HEARD AS A RASP WHERE TURNING THE WHOLE THING DOWN IS NOT."""
    loudest = float(np.abs(sound).max()) if sound.size else 0.0

    return sound / loudest * CEILING if loudest > CEILING else sound


def pinned(name):
    """ONE VOICE BY NAME, WHICH NO SETTING AND NO SENTENCE CAN MOVE."""
    return Voice(name=name)


def weights():
    """ONE MODEL FOR EVERY VOICE, READ OFF THE DISK ONCE PER RUN."""
    global loaded

    if loaded:
        return loaded

    if not whole():
        raise VoiceError(GET_THEM)

    try:
        from supertonic import TTS
    except ImportError as error:
        raise VoiceError(f"{GET_THEM} ({error})")

    # LEFT TO ITSELF ONNXRUNTIME TAKES EVERY CORE THE MACHINE HAS, WHICH ON A MAC IS SLOWER
    # THAN TAKING THE FAST ONES.
    loaded = TTS(model_dir=MODELS, auto_download=False, intra_op_num_threads=systems.cores())

    return loaded


def whole():
    """A VOICE IS THE GRAPHS AND AT LEAST ONE STYLE. AN EMPTY FOLDER IS NOT A VOICE."""
    return GRAPHS.is_dir() and any(GRAPHS.glob("*.onnx")) and bool(voices())


def voices():
    """EVERY STYLE ON THE DISK, IN THE ORDER THEY ARE WORTH HEARING RATHER THAN ALPHABETICAL."""
    if not STYLES.is_dir():
        return []

    found = {path.stem for path in STYLES.glob("*.json")}
    known = [name for name in VOICES if name in found]

    return known + sorted(found.difference(known))


def holds(language=ENGLISH):
    """THIS ENGINE SPEAKS ENGLISH, AND THIRTY OTHERS IT IS NOT ASKED FOR."""
    return language == ENGLISH


def installed(text=""):
    return voices()


def find(text=""):
    """THE VOICE TO SPEAK WITH, OR A COMPLAINT SAYING HOW TO GET ONE."""
    if not whole():
        raise VoiceError(GET_THEM)

    found = voices()

    # A NAME THAT IS NOT ONE OF ITS OWN, OR IS NOT DOWNLOADED, FALLS BACK QUIETLY.
    chosen = settings.get("voice.name")

    return chosen if chosen in found else (DEFAULT if DEFAULT in found else found[0])


def fetch():
    """THE MODEL ONTO DISK, BESIDE THE OTHERS RATHER THAN IN A CACHE OF ITS OWN."""
    from supertonic import TTS

    MODELS.mkdir(parents=True, exist_ok=True)
    TTS(model_dir=MODELS, auto_download=True)

    return MODELS
