"""SPEECH INTO TEXT, LOCALLY."""

from face import silence

silence.configure()  # KEEPS THIS IMPORTABLE ON ITS OWN. A NO-OP IF main.py RAN IT.

import whisperx

from face import show
from memory import settings

model = None
built = None


def wanted():
    return (
        settings.get("ears.model"),
        settings.get("ears.device"),
        settings.get("ears.language"),  # PINNED, DETECTION COSTS A PASS EVERY CALL.
    )


def load_model():
    """CALLED AT STARTUP, AND AGAIN WHEN A SETTING PICKS A DIFFERENT ONE."""
    global model, built

    asked = wanted()

    if model is not None and built == asked:
        return model

    size, device, language = asked

    try:
        model = whisperx.load_model(size, device, language=language)
        built = asked
    except Exception as error:
        if model is None:  # NOTHING TO FALL BACK ON. STARTING UP DESERVES TO FAIL.
            raise

        # A SIZE OR A DEVICE THIS MACHINE HAS NOT GOT. KEEP HEARING WITH THE OLD ONE.
        show.trouble(f"{size} on {device} would not load, still hearing with {built[0]} ({error})")

    return model


def transcribe(audio_file):
    audio = whisperx.load_audio(str(audio_file))
    result = load_model().transcribe(audio)

    return " ".join(segment["text"].strip() for segment in result["segments"]).strip()
