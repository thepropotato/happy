"""SPEECH INTO TEXT, LOCALLY."""

from face import silence

silence.configure()  # KEEPS THIS IMPORTABLE ON ITS OWN. A NO-OP IF main.py RAN IT.

import whisperx

DEVICE = "cpu"
LANGUAGE = "en"  # PINNED, DETECTION COSTS A PASS OVER THE AUDIO EVERY CALL.

SIZES = ["tiny", "base", "small", "medium", "large-v2", "large-v3", "turbo"]
CHOSEN = SIZES[3]

model = None


def load_model():
    """CALLED AT STARTUP, SO THE FIRST TAKE DOES NOT PAY FOR IT."""
    global model

    if model is None:
        model = whisperx.load_model(CHOSEN, DEVICE, language=LANGUAGE)

    return model


def transcribe(audio_file):
    audio = whisperx.load_audio(str(audio_file))
    result = load_model().transcribe(audio)

    return " ".join(segment["text"].strip() for segment in result["segments"]).strip()
