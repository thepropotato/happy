"""THE VOICE THAT MEANS IT: A SPEECH MODEL THAT DECIDES ITS OWN PAUSES AND EMPHASIS."""

import contextlib
import io
import os

import numpy as np

from bones.systems import on_mac
from memory import settings
from voice.engines import VoiceError

RATE = 24000

# THE 0.6B IS THE ONE THAT ANSWERS INSIDE A QUARTER SECOND. THE 1.7B SOUNDS A LITTLE BETTER
# AND TAKES ABOUT THREE TIMES AS LONG TO SAY ANYTHING.
REPOSITORY = "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit"

# HOW MUCH SOUND THE MODEL MAKES BEFORE HANDING THE FIRST OF IT BACK. LOWER STARTS SOONER.
INTERVAL = 1.0

VOICES = ["Ryan", "Eric", "Dylan", "Aiden", "Serena", "Vivian", "Uncle_Fu", "Ono_Anna", "Sohee"]

DEFAULT = "Ryan"

ENGLISH = "en"

GET_THEM = (
    "No expressive voice on this machine. Get it with:\n"
    "  python -m voice --get --engine expressive"
)

# IT RUNS ON APPLE'S OWN FRAMEWORK, SO THERE IS NOTHING TO INSTALL ANYWHERE ELSE. THE SMOOTH
# VOICE IS THE ONE THAT SPEAKS ON WINDOWS.
ELSEWHERE = "The expressive voice only runs on a Mac. Pick another engine in the settings."

# THE MODEL, BUILT ON FIRST ASK. IT IS TWO GIGABYTES, SO NEVER TWICE.
loaded = None

# IT WARNS ABOUT A MODEL TYPE IT THEN LOADS PERFECTLY WELL, AND COUNTS FILES IT ALREADY HAS,
# ON EVERY SINGLE START. NEITHER IS NEWS TO ANYBODY READING OUR LOG.
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")


def weights():
    global loaded

    if loaded is not None:
        return loaded

    if not on_mac():
        raise VoiceError(ELSEWHERE)

    try:
        from mlx_audio.tts.utils import load_model
    except ImportError as error:
        raise VoiceError(f"{GET_THEM} ({error})")

    # THE LOADER TALKS TO STDOUT ABOUT CODEBOOKS AND CHECKPOINTS, AND NONE OF IT IS OURS.
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            loaded = load_model(REPOSITORY)
    except Exception as error:
        raise VoiceError(f"The expressive voice would not load. {error}")

    return loaded


class Voice:
    """SENTENCES IN, SOUND OUT, WITH THE PAUSES WHERE THE WORDS PUT THEM."""

    rate = RATE

    def __init__(self, name=None, pace=None):
        self.pinned = name
        self.held = pace
        self.model = weights()
        self.name = name or find()

    def refit(self, text=""):
        """PICK UP A CHANGED VOICE. THERE IS ONE MODEL AND IT HOLDS EVERY VOICE, SO THIS ONLY
        EVER CHANGES A NAME."""
        if self.pinned is None:
            self.name = find(text)

    def stream(self, text):
        """A SENTENCE AS THE PIECES IT IS MADE OF, EACH HANDED OVER THE MOMENT IT EXISTS."""
        self.refit(text)

        for piece in self.model.generate(
            text=text,
            voice=self.name,
            lang_code=ENGLISH,
            stream=True,
            streaming_interval=INTERVAL,
            **self.styled(),
        ):
            sound = np.asarray(piece.audio, dtype=np.float32)

            if len(sound):
                yield sound

    def styled(self):
        """HOW IT SHOULD SOUND, WHERE SOMEBODY HAS SAID. THE MODEL TAKES THIS IN WORDS."""
        how = (settings.get("voice.manner") or "").strip()

        return {"instruct": how} if how else {}

    def say(self, text):
        parts = list(self.stream(text))

        return np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)

    def warm(self):
        """SAY ONE THING NOW, SO THE FIRST REAL ANSWER IS NOT THE ONE THAT PAYS FOR THIS."""
        self.say("Ready.")


def pinned(name):
    return Voice(name=name)


def voices():
    return list(VOICES)


def holds(language=ENGLISH):
    """THIS ENGINE SPEAKS ENGLISH. ANOTHER ONE IS ASKED FOR ANYTHING ELSE."""
    return language == ENGLISH


def installed(text=""):
    if not on_mac():
        return False

    try:
        import mlx_audio  # noqa: F401
    except ImportError:
        return False

    return True


def whole():
    return installed()


def find(text=""):
    wanted = settings.get("voice.name")

    return wanted if wanted in VOICES else DEFAULT


def fetch():
    """THE WEIGHTS ONTO DISK. THIS BLOCKS FOR AS LONG AS IT TAKES."""
    weights()

    return True
