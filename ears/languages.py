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

# THE TELUGU EAR IS vasista22'S, APACHE 2.0, OUT OF SPRING LAB AT IIT MADRAS. THEIR REPOSITORY
# HOLDS TORCH AND FLAX WEIGHTS AND NO ONNX AT ALL, SO ears.exporting MAKES THE GRAPHS OUT OF
# THEM AND THOSE GO UP AS ASSETS ON A RELEASE OF OURS, THE WAY THE LANGUAGE DETECTOR'S DO.
TELUGU = "vasista22/whisper-telugu-small"

RELEASE = "https://github.com/thepropotato/happy/releases/download/whisper-telugu-small-v1"

LANGUAGES = {
    "hi": {"repo": "onnx-community/whisper-hindi-small-ONNX", "quantization": "quantized"},
    "te": {"name": TELUGU, "release": RELEASE, "parts": LOCAL_PARTS},
}

DEFAULT = {"repo": "onnx-community/whisper-small", "quantization": "quantized"}

# ONE ATTEMPT EACH PER RUN. A FAILED DOWNLOAD SHOULD NOT RETRY ON EVERY SENTENCE.
getting = set()


def spoken():
    return (settings.get("ears.language") or "auto").strip().lower()


def picked(language=None):
    language = (spoken() if language is None else language).strip().lower()
    entry = LANGUAGES.get(language, DEFAULT)

    # A REPOSITORY IS BOTH WHAT A MODEL IS CALLED AND WHERE IT COMES FROM. A RELEASE IS ONLY
    # WHERE IT COMES FROM, SO THE OWNER'S NAME FOR IT IS CARRIED ALONGSIDE.
    name = entry.get("name") or entry.get("repo") or DEFAULT["repo"]

    return {
        "name": name,
        "release": entry.get("release", ""),
        "path": MODELS.parent / name.rsplit("/", 1)[-1],
        "quantization": entry.get("quantization"),
        "parts": entry.get("parts") or PARTS,
    }


def complete(choice):
    return choice["path"].is_dir() and all((choice["path"] / part).exists() for part in choice["parts"])


def download(language=None):
    """THE WEIGHTS, ONTO DISK. THIS BLOCKS FOR AS LONG AS IT TAKES."""
    choice = picked(language)

    if choice["release"]:
        return assets(choice)

    from huggingface_hub import snapshot_download

    snapshot_download(choice["name"], local_dir=choice["path"], allow_patterns=list(choice["parts"]))

    return choice["path"]


def assets(choice):
    """THE FILES OFF A RELEASE OF OUR OWN, WHICH IS HOW A MODEL WHOSE OWNER PUBLISHES NO ONNX
    STILL COMES FROM SOMEWHERE THAT NAMES THEM."""
    # requests CARRIES ITS OWN CERTIFICATES, AND urllib ON A PYTHON.ORG MAC HAS NONE.
    import requests

    choice["path"].mkdir(parents=True, exist_ok=True)

    for part in choice["parts"]:
        into = choice["path"] / part

        if into.exists():
            continue

        # BESIDE IT, THEN MOVED: A DOWNLOAD CUT OFF HALFWAY MUST NOT LOOK LIKE A MODEL.
        half = into.with_suffix(into.suffix + ".part")

        with requests.get(f"{choice['release']}/{part}", stream=True, timeout=30) as answer:
            answer.raise_for_status()

            with half.open("wb") as file:
                for lump in answer.iter_content(chunk_size=1 << 20):
                    file.write(lump)

        half.replace(into)

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
