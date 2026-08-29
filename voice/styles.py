"""THE VOICE FILES ON THIS MACHINE: WHAT IS HERE, WHICH ONE SPEAKS, AND GETTING MORE."""

import json
from pathlib import Path

from memory import settings
from voice.engines import VoiceError

MODELS = Path(__file__).resolve().parent.parent / "models" / "kokoro"
MODEL = MODELS / "model.onnx"
VOCAB = MODELS / "vocab.json"
STYLES = MODELS / "voices"
SUFFIX = "*.bin"

REPO = "onnx-community/Kokoro-82M-v1.0-ONNX"
WEIGHTS = "onnx/model.onnx"
WORDS = "tokenizer.json"

# BEST FIRST, BY HOW MUCH EACH WAS TRAINED ON RATHER THAN BY ACCENT: THE FIRST TWO ARE THE
# ONLY ONES GRADED A, AND EVERY MALE VOICE IN THIS MODEL IS C OR BELOW AND SOUNDS IT. THE
# FIRST NAME HERE IS WHAT SPEAKS WHEN NOBODY HAS PICKED ONE.
VOICES = ["af_heart", "af_bella", "bf_emma", "af_nicole", "am_puck", "am_fenrir",
          "am_michael", "bm_george", "af_sarah", "af_aoede", "bm_fable", "am_onyx"]

GET_THEM = f"No voice in {MODELS}. Get one with:\n  python -m voice --get"


def whole():
    """A VOICE IS A MODEL, AN ALPHABET AND AT LEAST ONE STYLE. TWO OF THREE IS NOT A VOICE."""
    return MODEL.exists() and VOCAB.exists() and bool(voices())


def voices():
    """EVERY STYLE ON THE DISK, IN THE ORDER THEY ARE WORTH HEARING RATHER THAN ALPHABETICAL."""
    if not STYLES.is_dir():
        return []

    found = {path.stem for path in STYLES.glob(SUFFIX)}
    known = [name for name in VOICES if name in found]

    return known + sorted(found.difference(known))


def holds():
    """WHETHER A VOICE IS ALREADY ON THE DISK."""
    return bool(voices())


def installed(text=""):
    return voices()


def find(text=""):
    """THE VOICE TO SPEAK WITH, OR A COMPLAINT SAYING HOW TO GET ONE."""
    found = voices()

    if not found:
        raise VoiceError(GET_THEM)

    # A NAME THAT IS NO LONGER INSTALLED FALLS BACK QUIETLY.
    chosen = settings.get("voice.name")

    return chosen if chosen in found else found[0]


def fetch():
    """THE MODEL, ITS ALPHABET AND THE VOICES, FETCHED THROUGH A CLIENT THAT HAS ROOT
    CERTIFICATES. urllib HAS NONE ON THIS MACHINE'S PYTHON."""
    import shutil

    from huggingface_hub import hf_hub_download

    STYLES.mkdir(parents=True, exist_ok=True)

    if not MODEL.exists():
        shutil.copyfile(hf_hub_download(REPO, WEIGHTS), MODEL)

    if not VOCAB.exists():
        alphabet = json.loads(Path(hf_hub_download(REPO, WORDS)).read_text(encoding="utf-8"))
        VOCAB.write_text(json.dumps(alphabet["model"]["vocab"]), encoding="utf-8")

    for name in VOICES:
        shutil.copyfile(hf_hub_download(REPO, f"voices/{name}.bin"), STYLES / f"{name}.bin")

    return MODELS
