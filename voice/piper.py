"""THE VOICE ITSELF. A SMALL ONNX MODEL THAT ANSWERS IN UNDER TWENTY MILLISECONDS.

PHONEMES COME FROM AN ESPEAK-NG THAT SHIPS INSIDE THE PACKAGE, SO THERE IS
NOTHING TO INSTALL BESIDE THE VOICE FILE AND IT BEHAVES THE SAME ON WINDOWS.

GET A VOICE:
    python -m piper.download_voices en_US-hfc_male-medium --download-dir models/piper
"""

from pathlib import Path

import numpy as np

MODELS = Path(__file__).resolve().parent.parent / "models" / "piper"
SUFFIX = "*.onnx"

# WHICH FILE, WHEN THERE IS MORE THAN ONE. EMPTY TAKES WHATEVER IS THERE.
VOICE = ""

# BELOW ONE IS FASTER SPEECH, WHICH READS AS SOMEONE WITH THE ANSWER IN HAND.
LENGTH_SCALE = 0.95

RATE = 22050  # ONLY THE MUTE ONE'S. A REAL VOICE REPORTS ITS OWN.

GET_THEM = (
    f"No voice in {MODELS}. Get one with:\n"
    "  python -m piper.download_voices en_US-hfc_male-medium --download-dir models/piper"
)


class VoiceError(Exception):
    pass


class Voice:
    """SENTENCES IN, SOUND OUT. THE ONLY PART THAT KNOWS WHAT A MODEL IS."""

    def __init__(self, path=None, length=LENGTH_SCALE):
        from piper import PiperVoice, SynthesisConfig

        self.path = path or find()
        self.voice = PiperVoice.load(self.path)
        self.rate = self.voice.config.sample_rate
        self.how = SynthesisConfig(length_scale=length)

    def say(self, text):
        # ONE SENTENCE COMES BACK IN A HANDFUL OF CHUNKS. THE PLAYER WANTS ONE.
        parts = [chunk.audio_float_array for chunk in self.voice.synthesize(text, self.how)]

        return np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)

    def warm(self):
        """SYNTHESISE ONCE NOW. THE FIRST CALL COSTS THIRTY TIMES THE REST."""
        self.say("Ready.")


class Mute:
    """STANDS IN WHEN THE VOICE WILL NOT LOAD, SO NOTHING ELSE NEEDS AN IF."""

    rate = RATE

    def say(self, text):
        return np.zeros(0, dtype=np.float32)

    def warm(self):
        pass


def whole(path):
    """A VOICE IS TWO FILES. HALF A DOWNLOAD IS NOT A VOICE."""
    return path.exists() and path.with_suffix(".onnx.json").exists()


def find():
    """THE VOICE FILE, OR A COMPLAINT SAYING HOW TO GET ONE."""
    if VOICE:
        chosen = MODELS / f"{VOICE}.onnx"

        if not whole(chosen):
            raise VoiceError(f"No complete voice at {chosen}.\n{GET_THEM}")

        return chosen

    found = [path for path in sorted(MODELS.glob(SUFFIX)) if whole(path)] if MODELS.is_dir() else []

    if not found:
        raise VoiceError(GET_THEM)

    return found[0]
