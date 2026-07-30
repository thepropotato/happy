"""THE VOICE ITSELF. A SMALL ONNX MODEL THAT ANSWERS IN UNDER TWENTY MILLISECONDS.

PHONEMES COME FROM AN ESPEAK-NG THAT SHIPS INSIDE THE PACKAGE, SO THERE IS
NOTHING TO INSTALL BESIDE THE VOICE FILE AND IT BEHAVES THE SAME ON WINDOWS.

GET A VOICE:
    python -m piper.download_voices en_US-hfc_male-medium --download-dir models/piper
"""

from pathlib import Path

import numpy as np

from memory import settings
from voice.engines import VoiceError

MODELS = Path(__file__).resolve().parent.parent / "models" / "piper"
SUFFIX = "*.onnx"

GET_THEM = (
    f"No voice in {MODELS}. Get one with:\n"
    "  python -m piper.download_voices en_US-hfc_male-medium --download-dir models/piper"
)


class Voice:
    """SENTENCES IN, SOUND OUT. THE ONLY PART THAT KNOWS WHAT A MODEL IS."""

    def __init__(self, path=None, length=None):
        self.pinned = path  # HANDED A FILE MEANS THE SETTING NEVER MOVES IT.
        self.path = None
        self.pace = None
        self.voice = None
        self.rate = None  # A REAL VOICE REPORTS ITS OWN, AND load() ASKS IT.

        self.load(Path(path) if path else find(), length)

    def load(self, path, length=None):
        from piper import PiperVoice, SynthesisConfig

        self.voice = PiperVoice.load(path)
        self.path = path
        self.rate = self.voice.config.sample_rate
        self.pace = settings.get("voice.pace") if length is None else length

        # BELOW ONE IS FASTER SPEECH, WHICH READS AS SOMEONE WITH THE ANSWER IN HAND.
        self.how = SynthesisConfig(length_scale=self.pace)

    def refit(self):
        """PICK UP A CHANGED VOICE OR PACE. RELOADING COSTS A FEW MILLISECONDS."""
        wanted = self.pinned or find()

        if Path(wanted) != self.path or settings.get("voice.pace") != self.pace:
            self.load(Path(wanted))

    def say(self, text):
        self.refit()

        # ONE SENTENCE COMES BACK IN A HANDFUL OF CHUNKS. THE PLAYER WANTS ONE.
        parts = [chunk.audio_float_array for chunk in self.voice.synthesize(text, self.how)]

        return np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)

    def warm(self):
        """SYNTHESISE ONCE NOW. THE FIRST CALL COSTS THIRTY TIMES THE REST."""
        self.say("Ready.")


def whole(path):
    """A VOICE IS TWO FILES. HALF A DOWNLOAD IS NOT A VOICE."""
    return path.exists() and path.with_suffix(".onnx.json").exists()


def installed():
    """EVERY VOICE ON THIS MACHINE, BY NAME, FOR SOMETHING DRAWING A LIST."""
    if not MODELS.is_dir():
        return []

    return [path.stem for path in sorted(MODELS.glob(SUFFIX)) if whole(path)]


def find():
    """THE VOICE FILE, OR A COMPLAINT SAYING HOW TO GET ONE."""
    chosen = settings.get("voice.name")

    if chosen:
        wanted = MODELS / f"{chosen}.onnx"

        if whole(wanted):
            return wanted

    found = [path for path in sorted(MODELS.glob(SUFFIX)) if whole(path)] if MODELS.is_dir() else []

    if not found:
        raise VoiceError(GET_THEM)

    return found[0]  # A NAME THAT IS NO LONGER INSTALLED FALLS BACK, IT DOES NOT FAIL.
