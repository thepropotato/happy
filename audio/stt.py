import logs

logs.configure()  # NO-OP EXTRA COST IF MAIN.PY ALREADY DID IT; KEEPS STT IMPORTABLE ON ITS OWN.

import whisperx

DEVICE = "cpu"
LANGUAGE = "en"  # PINNED, AUTO DETECTION COSTS A PASS OVER THE AUDIO EVERY CALL.

MODEL_VARIANTS = ["tiny", "base", "small", "medium", "large-v2", "large-v3", "turbo"]
SELECTED_MODEL_VARIANT_INDEX = 3
SELECTED_MODEL = MODEL_VARIANTS[SELECTED_MODEL_VARIANT_INDEX]

model = None


def load_model():  # CALLED AT STARTUP, SO THE FIRST TAKE IS NOT THE ONE THAT PAYS FOR IT.
    global model

    if model is None:
        model = whisperx.load_model(SELECTED_MODEL, DEVICE, language=LANGUAGE)

    return model


def transcribe_speech(audio_file_path):
    audio = whisperx.load_audio(str(audio_file_path))
    result = load_model().transcribe(audio)

    return " ".join(segment["text"].strip() for segment in result["segments"]).strip()
