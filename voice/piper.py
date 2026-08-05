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
DEFAULT = "en_US-hfc_male-medium"
VOICES_BY_LANGUAGE = {
    "hi": "hi_IN-pratham-medium",
    "te": "te_IN-venkatesh-medium",
}
TELUGU = "te"
HINDI = "hi"
FALLBACK = "en"

GET_THEM = (
    f"No voice in {MODELS}. Get one with:\n"
    f"  python -m piper.download_voices {DEFAULT} --download-dir models/piper"
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

        # BELOW ONE IS FASTER SPEECH.
        self.how = SynthesisConfig(length_scale=self.pace)

    def refit(self, text=""):
        """PICK UP A CHANGED VOICE OR PACE. RELOADING COSTS A FEW MILLISECONDS."""
        wanted = self.pinned or find(text)

        if Path(wanted) != self.path or settings.get("voice.pace") != self.pace:
            self.load(Path(wanted))

    def say(self, text):
        self.refit(text)

        parts = [chunk.audio_float_array for chunk in self.voice.synthesize(text, self.how)]

        return np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)

    def warm(self):
        """SYNTHESISE ONCE NOW. THE FIRST CALL COSTS THIRTY TIMES THE REST."""
        self.say("Ready.")


def whole(path):
    """A VOICE IS TWO FILES. HALF A DOWNLOAD IS NOT A VOICE."""
    return path.exists() and path.with_suffix(".onnx.json").exists()


def language(path):
    """THE LANGUAGE PREFIX FROM A VOICE FILE NAME."""
    name = Path(path).stem
    prefix = name.split("-", 1)[0].lower()

    return prefix.split("_", 1)[0]


def detected(text):
    telugu = 0
    hindi = 0

    for character in (text or ""):
        point = ord(character)

        if 0x0C00 <= point <= 0x0C7F:
            telugu += 1
        elif 0x0900 <= point <= 0x097F:
            hindi += 1

    if telugu > hindi and telugu > 0:
        return TELUGU

    if hindi > telugu and hindi > 0:
        return HINDI

    return FALLBACK


def target_language():
    return (settings.get("ears.language") or "auto").strip().lower()


def voices():
    if not MODELS.is_dir():
        return []

    return [path for path in sorted(MODELS.glob(SUFFIX)) if whole(path)]


def has_language(wanted):
    return any(language(path) == wanted for path in voices())


def ranked(found, target):
    matching = [path for path in found if language(path) == target]
    rest = [path for path in found if language(path) != target]

    return matching + rest


def installed(text=""):
    """EVERY VOICE ON THIS MACHINE, BY NAME, FOR SOMETHING DRAWING A LIST."""
    return [path.stem for path in ranked(voices(), detected(text))]


def find(text=""):
    """THE VOICE FILE, OR A COMPLAINT SAYING HOW TO GET ONE."""
    found = voices()

    if not found:
        raise VoiceError(GET_THEM)

    target = detected(text)
    preferred = ranked(found, target)

    if preferred and language(preferred[0]) == target:
        return preferred[0]

    chosen = settings.get("voice.name")

    if chosen:
        wanted = MODELS / f"{chosen}.onnx"

        if whole(wanted):
            return wanted

    return found[0]  # A NAME THAT IS NO LONGER INSTALLED FALLS BACK, IT DOES NOT FAIL.


def fetch(language=None):
    from piper.download_voices import download_voice

    chosen = VOICES_BY_LANGUAGE.get((language or "").strip().lower(), DEFAULT)
    download_voice(chosen, MODELS)

    return MODELS
