"""SPEECH INTO TEXT, LOCALLY.

GET THE WEIGHTS:
    python -m ears --get
"""

from pathlib import Path

import numpy as np

from face import show
from memory import settings

MODELS = Path(__file__).resolve().parent.parent / "models" / "parakeet"

NAME = "nemo-parakeet-tdt-0.6b-v2"
REPO = "istupakov/parakeet-tdt-0.6b-v2-onnx"
QUANTISATION = "int8"

# FOUR FILES, AND HALF A DOWNLOAD IS NOT A MODEL.
PARTS = (
    "config.json",
    "vocab.txt",
    "encoder-model.int8.onnx",
    "decoder_joint-model.int8.onnx",
)

RATE = 16000

# ONNXRUNTIME WOULD PUT COREML FIRST, WHICH IS UNMEASURED ON A 650 MB ENCODER.
PROVIDERS = {"cpu": ["CPUExecutionProvider"]}

GET_IT = f"No speech model in {MODELS}. Get it with:\n  python -m ears --get"

model = None
built = None


class EarsError(Exception):
    pass


def wanted():
    return settings.get("ears.device")


def whole():
    return all((MODELS / part).exists() for part in PARTS)


def load_model():
    """CALLED AT STARTUP, AND AGAIN WHEN A SETTING PICKS A DIFFERENT ONE."""
    global model, built

    asked = wanted()

    if model is not None and built == asked:
        return model

    if not whole():
        raise EarsError(GET_IT)

    import onnx_asr

    try:
        model = onnx_asr.load_model(
            NAME, MODELS, quantization=QUANTISATION, providers=PROVIDERS.get(asked)
        )
        built = asked
    except Exception as error:
        if model is None:
            raise

        show.trouble(f"{asked} would not load, still hearing on {built} ({error})")

    return model


def transcribe(audio_file):
    return load_model().recognize(str(audio_file)).strip()


def warm():
    """RECOGNISE ONCE NOW. THE FIRST CALL IS THE ONE THAT BUILDS THE SESSION."""
    load_model().recognize(np.zeros(RATE // 2, dtype=np.float32), sample_rate=RATE)


def fetch():
    """THE WEIGHTS, INTO models/parakeet. ONLY EVER RUN BY HAND."""
    from huggingface_hub import snapshot_download

    snapshot_download(REPO, local_dir=MODELS, allow_patterns=list(PARTS))

    return MODELS
