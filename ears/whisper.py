"""SPEECH INTO TEXT, LOCALLY, WITH WHISPER.

GET THE WEIGHTS:
    python -m ears --get
"""

import os
from pathlib import Path

import numpy as np
import requests

from ears.engines import EarsError
from face import show
from memory import settings

MODELS = Path(__file__).resolve().parent.parent / "models" / "whisper"

# PARTIAL DOWNLOADS DO NOT COUNT AS READY.
PARTS = (
    "config.json",
    "vocab.json",
    "added_tokens.json",
    "onnx/encoder_model_quantized.onnx",
    "onnx/decoder_model_merged_quantized.onnx",
)

LOCAL_PARTS = (
    "config.json",
    "vocab.json",
    "added_tokens.json",
    "encoder_model.onnx",
    "decoder_model_merged.onnx",
)

LANGUAGES = {
    "hi": {"repo": "onnx-community/whisper-hindi-small-ONNX", "quantization": "quantized"},
    "te": {"repo": "Susipriya/whisper-telugu-small-onnx", "parts": LOCAL_PARTS},
}

DEFAULT = {"repo": "onnx-community/whisper-small", "quantization": "quantized"}

RATE = 16000

# CPU IS THE SAFE BASELINE EVERYWHERE.
PROVIDERS = {"cpu": ["CPUExecutionProvider"]}


def missing(path):
    return f"No speech model in {path}. Get it with:\n  python -m ears --get"
model = None
built = None
cached = {}


def wanted():
    return settings.get("ears.device")
def spoken():
    return (settings.get("ears.language") or "auto").strip().lower()


def detect_language(audio_file):
    key = os.environ.get("LLM_API_KEY")
    if not key:
        return None

    try:
        with open(audio_file, "rb") as file:
            response = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {key}"},
                data={"model": "whisper-1", "response_format": "verbose_json"},
                files={"file": (Path(audio_file).name, file)},
                timeout=15,
            )

        response.raise_for_status()
        heard = (response.json().get("language") or "").strip().lower()
        code = {"hindi": "hi", "telugu": "te"}.get(heard)

        return code if code in LANGUAGES else None
    except Exception:
        return None


def picked(language=None):
    language = (spoken() if language is None else language).strip().lower()
    entry = LANGUAGES.get(language, DEFAULT)

    repo = entry.get("repo") or DEFAULT["repo"]
    path = MODELS.parent / repo.rsplit("/", 1)[-1]

    return {
        "name": repo,
        "path": path,
        "quantization": entry.get("quantization"),
        "parts": entry.get("parts") or PARTS,
    }


def complete(choice):
    return choice["path"].is_dir() and all((choice["path"] / part).exists() for part in choice["parts"])


def whole():
    return complete(picked())


def load_model(language=None):
    """CALLED AT STARTUP, AND AGAIN WHEN A SETTING PICKS A DIFFERENT ONE."""
    global model, built, cached

    asked = wanted()
    choice = picked(language)
    state = (asked, choice["name"], str(choice["path"]), choice["quantization"])

    if state in cached:
        model = cached[state]
        built = state
        return model

    if not complete(choice):
        raise EarsError(missing(choice["path"]))

    import onnx_asr

    try:
        if choice["quantization"]:
            model = onnx_asr.load_model(
                choice["name"],
                choice["path"],
                quantization=choice["quantization"],
                providers=PROVIDERS.get(asked),
            )
        else:
            model = onnx_asr.load_model(
                choice["name"],
                choice["path"],
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
    language = spoken()
    source = str(audio_file)

    if language != "auto":
        heard = load_model(language).recognize(source, language=language).strip()
        return "" if looping(heard) else heard
    found = detect_language(source)

    if found in LANGUAGES:
        heard = load_model(found).recognize(source, language=found).strip()
        return "" if looping(heard) else heard

    # WHISPER AUTO-DETECTS LANGUAGE WHEN NONE IS FORCED.
    heard = load_model("auto").recognize(source).strip()
    return "" if looping(heard) else heard


def looping(text, most=5):
    run = 1
    last = None

    for character in text:
        if character == last:
            run += 1

            if run > most:
                return True
        else:
            last = character
            run = 1

    return False


def warm():
    """RECOGNISE ONCE NOW. THE FIRST CALL IS THE ONE THAT BUILDS THE SESSION."""
    load_model(spoken()).recognize(np.zeros(RATE // 2, dtype=np.float32), sample_rate=RATE)


def fetch():
    """THE WEIGHTS, INTO models/whisper. ONLY EVER RUN BY HAND."""
    choice = picked()
    from huggingface_hub import snapshot_download

    snapshot_download(choice["name"], local_dir=choice["path"], allow_patterns=list(choice["parts"]))

    return choice["path"]
