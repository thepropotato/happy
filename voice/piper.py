"""THE VOICE ITSELF."""

from pathlib import Path

import numpy as np

import tongue
from memory import settings
from voice.collecting import collect
from voice.engines import VoiceError

MODELS = Path(__file__).resolve().parent.parent / "models" / "piper"
SUFFIX = "*.onnx"
DEFAULT = "en_US-hfc_male-medium"
REPO = "rhasspy/piper-voices"
VOICES_BY_LANGUAGE = {
    "hi": "hi_IN-pratham-medium",
    "te": "te_IN-venkatesh-medium",
}

GET_THEM = f"No voice in {MODELS}. Get one with:\n  python -m voice --get"


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

        # BELOW ONE IS FASTER SPEECH. THE TWO NOISE FIGURES ARE THE VOICE'S OWN, TUNED WHEN
        # IT WAS TRAINED: DROPPING THEM FOR THE LIBRARY'S DEFAULTS FLATTENS ITS PROSODY.
        self.how = SynthesisConfig(
            length_scale=self.pace,
            noise_scale=self.voice.config.noise_scale,
            noise_w_scale=self.voice.config.noise_w_scale,
        )

    def refit(self, text=""):
        """PICK UP A CHANGED VOICE OR PACE. RELOADING COSTS A FEW MILLISECONDS."""
        wanted = self.pinned or find(text)

        if Path(wanted) != self.path or settings.get("voice.pace") != self.pace:
            self.load(Path(wanted))

    def say(self, text):
        parts = list(self.stream(text))

        return np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)

    def stream(self, text):
        """ONE SENTENCE AS THE PIECES IT IS MADE OF, PASSED ON AS THE MODEL FINISHES EACH."""
        self.refit(text)

        for chunk in self.voice.synthesize(text, self.how):
            yield chunk.audio_float_array

    def warm(self):
        """SYNTHESISE ONCE NOW. THE FIRST CALL COSTS THIRTY TIMES THE REST."""
        self.say("Ready.")


def pinned(name):
    """ONE VOICE FILE BY NAME, WHICH NO SETTING AND NO SENTENCE CAN MOVE."""
    return Voice(path=MODELS / f"{name}.onnx")


def whole(path):
    """A VOICE IS TWO FILES. HALF A DOWNLOAD IS NOT A VOICE."""
    return path.exists() and path.with_suffix(".onnx.json").exists()


def language(path):
    """THE LANGUAGE PREFIX FROM A VOICE FILE NAME."""
    name = Path(path).stem
    prefix = name.split("-", 1)[0].lower()

    return prefix.split("_", 1)[0]


def voices():
    if not MODELS.is_dir():
        return []

    return [path for path in sorted(MODELS.glob(SUFFIX)) if whole(path)]


def holds(wanted):
    """WHETHER A VOICE FOR THIS LANGUAGE IS ALREADY ON THE DISK."""
    return any(language(path) == wanted for path in voices())


def ranked(found, target):
    matching = [path for path in found if language(path) == target]
    rest = [path for path in found if language(path) != target]

    return matching + rest


def installed(text=""):
    """EVERY VOICE ON THIS MACHINE, BY NAME, FOR SOMETHING DRAWING A LIST."""
    return [path.stem for path in ranked(voices(), tongue.reading(text))]


def find(text=""):
    """THE VOICE FILE, OR A COMPLAINT SAYING HOW TO GET ONE."""
    found = voices()

    if not found:
        raise VoiceError(GET_THEM)

    # A MIXED SENTENCE GOES TO THE VOICE THAT CAN READ ITS HARDEST SCRIPT, NOT ITS COMMONEST.
    target = tongue.reading(text)
    preferred = ranked(found, target)

    if preferred and language(preferred[0]) == target:
        return preferred[0]

    collect(target, VOICES_BY_LANGUAGE, fetch)

    chosen = settings.get("voice.name")

    if chosen:
        wanted = MODELS / f"{chosen}.onnx"

        if whole(wanted):
            return wanted

    return found[0]  # A NAME THAT IS NO LONGER INSTALLED FALLS BACK, IT DOES NOT FAIL.


def wherein(name):
    """THEY ARE KEPT AT hi/hi_IN/pratham/medium/hi_IN-pratham-medium, SPELT OUT OF THE NAME."""
    parts = name.split("-")
    region, quality = parts[0], parts[-1]
    speaker = "-".join(parts[1:-1])

    return f"{region.split('_')[0]}/{region}/{speaker}/{quality}/{name}"


def fetch(language=None):
    """PIPER'S OWN DOWNLOADER GOES OUT THROUGH urllib, WHICH HAS NO CERTIFICATES ON MACOS."""
    import shutil

    from huggingface_hub import hf_hub_download

    chosen = VOICES_BY_LANGUAGE.get((language or "").strip().lower(), DEFAULT)
    where = wherein(chosen)
    MODELS.mkdir(parents=True, exist_ok=True)

    for suffix in ("onnx", "onnx.json"):
        got = hf_hub_download(REPO, f"{where}.{suffix}")
        shutil.copyfile(got, MODELS / f"{chosen}.{suffix}")

    return MODELS
