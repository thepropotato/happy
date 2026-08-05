"""WHICH MODEL EACH LANGUAGE IS HEARD BY, AND GETTING THAT MODEL ONTO THIS MACHINE."""

import threading
from pathlib import Path

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

# ONE ATTEMPT EACH PER RUN. A FAILED DOWNLOAD SHOULD NOT RETRY ON EVERY SENTENCE.
getting = set()


def spoken():
    return (settings.get("ears.language") or "auto").strip().lower()


def picked(language=None):
    language = (spoken() if language is None else language).strip().lower()
    entry = LANGUAGES.get(language, DEFAULT)

    repo = entry.get("repo") or DEFAULT["repo"]

    return {
        "name": repo,
        "path": MODELS.parent / repo.rsplit("/", 1)[-1],
        "quantization": entry.get("quantization"),
        "parts": entry.get("parts") or PARTS,
    }


def complete(choice):
    return choice["path"].is_dir() and all((choice["path"] / part).exists() for part in choice["parts"])


def download(language=None):
    """THE WEIGHTS, ONTO DISK. THIS BLOCKS FOR AS LONG AS IT TAKES."""
    from huggingface_hub import snapshot_download

    choice = picked(language)
    snapshot_download(choice["name"], local_dir=choice["path"], allow_patterns=list(choice["parts"]))

    return choice["path"]


def collect(language):
    """GET IT BEHIND THE CONVERSATION. NOBODY WAITS MID SENTENCE FOR A DOWNLOAD."""
    if language in getting:
        return

    getting.add(language)
    show.note(f"Getting the {language} speech model. This take is heard by the general one.")

    threading.Thread(target=pull, args=(language,), daemon=True).start()


def pull(language):
    try:
        download(language)
        show.note(f"The {language} speech model is ready.")
    except Exception as error:
        show.trouble(f"Could not get the {language} speech model ({error})")
