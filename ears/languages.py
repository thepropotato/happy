"""WHICH MODEL ENGLISH IS HEARD BY, AND GETTING THAT MODEL ONTO THIS MACHINE."""

from pathlib import Path

MODELS = Path(__file__).resolve().parent.parent / "models" / "whisper"

# PARTIAL DOWNLOADS DO NOT COUNT AS READY.
PARTS = (
    "config.json",
    "vocab.json",
    "added_tokens.json",
    "onnx/encoder_model_quantized.onnx",
    "onnx/decoder_model_merged_quantized.onnx",
)

# small MISHEARS ORDINARY WORDS INTO NUMBERS ("unread" CAME BACK AS "100") AND GREEDY
# DECODING GIVES IT NO SECOND GUESS TO FALL BACK ON, SO THE SIZE IS THE ONLY FIX.
DEFAULT = {"repo": "onnx-community/whisper-medium-ONNX", "quantization": "quantized"}


def picked():
    """THE ONE MODEL THERE IS."""
    return {
        "name": DEFAULT["repo"],
        "path": MODELS.parent / DEFAULT["repo"].rsplit("/", 1)[-1],
        "quantization": DEFAULT["quantization"],
        "parts": PARTS,
    }


def complete(choice):
    return choice["path"].is_dir() and all((choice["path"] / part).exists() for part in choice["parts"])


def download():
    """THE WEIGHTS, ONTO DISK. THIS BLOCKS FOR AS LONG AS IT TAKES."""
    from huggingface_hub import snapshot_download

    choice = picked()

    snapshot_download(choice["name"], local_dir=choice["path"], allow_patterns=list(choice["parts"]))

    return choice["path"]
