"""THE VOICE FILES ON THIS MACHINE: WHAT IS HERE, WHICH ONE SPEAKS, AND GETTING MORE."""

import json
from pathlib import Path

import tongue
from memory import settings
from voice import engines
from voice.collecting import collect
from voice.engines import ELSEWHERE, VoiceError

MODELS = Path(__file__).resolve().parent.parent / "models" / "kokoro"
MODEL = MODELS / "model.onnx"
VOCAB = MODELS / "vocab.json"
STYLES = MODELS / "voices"
SUFFIX = "*.bin"

REPO = "onnx-community/Kokoro-82M-v1.0-ONNX"
WEIGHTS = "onnx/model.onnx"
WORDS = "tokenizer.json"

# EVERY VOICE CARRIES ITS LANGUAGE IN THE FIRST LETTER OF ITS NAME AND ITS SEX IN THE SECOND.
LANGUAGES = {"a": "en", "b": "en", "h": "hi"}

# BEST FIRST, BY HOW MUCH EACH WAS TRAINED ON RATHER THAN BY ACCENT: THE FIRST TWO ARE THE
# ONLY ONES GRADED A, AND EVERY MALE VOICE IN THIS MODEL IS C OR BELOW AND SOUNDS IT. THE
# FIRST NAME HERE IS WHAT SPEAKS WHEN NOBODY HAS PICKED ONE.
VOICES_BY_LANGUAGE = {
    "en": ["af_heart", "af_bella", "bf_emma", "af_nicole", "am_puck", "am_fenrir",
           "am_michael", "bm_george", "af_sarah", "af_aoede", "bm_fable", "am_onyx"],
    "hi": ["hf_alpha", "hm_omega", "hf_beta", "hm_psi"],
}

GET_THEM = f"No voice in {MODELS}. Get one with:\n  python -m voice --get"


def whole():
    """A VOICE IS A MODEL, AN ALPHABET AND AT LEAST ONE STYLE. TWO OF THREE IS NOT A VOICE."""
    return MODEL.exists() and VOCAB.exists() and bool(voices())


def language(name):
    return LANGUAGES.get((name or "")[:1], "en")


def voices():
    """EVERY STYLE ON THE DISK, IN THE ORDER THEY ARE WORTH HEARING RATHER THAN ALPHABETICAL."""
    if not STYLES.is_dir():
        return []

    found = {path.stem for path in STYLES.glob(SUFFIX)}
    known = [name for each in VOICES_BY_LANGUAGE.values() for name in each if name in found]

    return known + sorted(found.difference(known))


def holds(wanted):
    """WHETHER A VOICE FOR THIS LANGUAGE IS ALREADY ON THE DISK, WHOSEVER VOICE IT IS."""
    if wanted in ELSEWHERE:
        return engines.part(ELSEWHERE[wanted]).holds(wanted)

    return any(language(name) == wanted for name in voices())


def ranked(found, target):
    """THE ONES THAT SPEAK THIS LANGUAGE FIRST, EACH GROUP STILL IN THE ORDER IT CAME IN."""
    return sorted(found, key=lambda name: language(name) != target)


def installed(text=""):
    return ranked(voices(), tongue.reading(text))


def find(text=""):
    """THE VOICE TO SPEAK THIS IN, OR A COMPLAINT SAYING HOW TO GET ONE."""
    found = voices()

    if not found:
        raise VoiceError(GET_THEM)

    # A MIXED SENTENCE GOES TO THE VOICE THAT CAN READ ITS HARDEST SCRIPT, NOT ITS COMMONEST.
    target = tongue.reading(text)
    preferred = ranked(found, target)

    if language(preferred[0]) != target:
        collect(target, VOICES_BY_LANGUAGE, fetch)

        return preferred[0]

    # A NAME THAT IS NO LONGER INSTALLED, OR SPEAKS ANOTHER LANGUAGE, FALLS BACK QUIETLY.
    chosen = settings.get("voice.name")

    return chosen if chosen in preferred and language(chosen) == target else preferred[0]


def fetch(wanted=None):
    """THE MODEL, ITS ALPHABET AND THE VOICES FOR ONE LANGUAGE, FETCHED THROUGH A CLIENT THAT
    HAS ROOT CERTIFICATES. urllib HAS NONE ON THIS MACHINE'S PYTHON."""
    import shutil

    from huggingface_hub import hf_hub_download

    wanted = (wanted or "").strip().lower() or "en"

    if wanted in ELSEWHERE:
        return engines.part(ELSEWHERE[wanted]).fetch(wanted)

    STYLES.mkdir(parents=True, exist_ok=True)

    if not MODEL.exists():
        shutil.copyfile(hf_hub_download(REPO, WEIGHTS), MODEL)

    if not VOCAB.exists():
        alphabet = json.loads(Path(hf_hub_download(REPO, WORDS)).read_text(encoding="utf-8"))
        VOCAB.write_text(json.dumps(alphabet["model"]["vocab"]), encoding="utf-8")

    for name in VOICES_BY_LANGUAGE.get(wanted, VOICES_BY_LANGUAGE["en"]):
        shutil.copyfile(hf_hub_download(REPO, f"voices/{name}.bin"), STYLES / f"{name}.bin")

    return MODELS
