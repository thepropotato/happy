"""WHERE SPEAKING HAPPENS."""

import wave

import numpy as np

from memory import settings
from voice.engines import VoiceError, attempt, build, chosen, installed, names, part
from voice.mute import Mute
from voice.speaker import Speaker

CHANNELS = 1
WIDTH_BYTES = 2
FULL = 32767

ENGLISH = "en"

# ONE LINE PER LANGUAGE, BECAUSE A SENTENCE IS SPOKEN BY WHICHEVER VOICE CAN READ ITS SCRIPT AND
# AN ENGLISH LINE WOULD BE ANSWERED BY AN ENGLISH VOICE WHATEVER IS PICKED.
SAMPLES = {
    "en": "Hello, I'm Happy. This is what I sound like.",
    "hi": "नमस्ते, मैं हैपी हूँ। मेरी आवाज़ ऐसी है।",
    "te": "నమస్కారం, నేను హ్యాపీ. నా గొంతు ఇలా ఉంటుంది.",
}

__all__ = [
    "Mute",
    "SAMPLES",
    "Speaker",
    "VoiceError",
    "attempt",
    "chosen",
    "create",
    "installed",
    "names",
    "sample",
    "spoken",
]


def create(**kwargs):
    """A SPEAKER, PLUS THE REASON IT IS MUTE WHEN IT IS."""
    voice, why = attempt(**kwargs)

    return Speaker(voice), why


def spoken(name=None):
    """THE LANGUAGE OF ONE VOICE, OR OF THE ONE THAT IS SET WHEN NOBODY NAMED ONE. ONLY THE
    ENGINE HOLDING IT CAN SAY."""
    try:
        return part().language(name or settings.get("voice.name") or "") or ENGLISH
    except Exception:
        return ENGLISH


def sample(name=None):
    """THE LINE TO SAY FOR SOMEBODY WHO WANTS TO HEAR A VOICE BEFORE THEY PICK IT."""
    return SAMPLES.get(spoken(name), SAMPLES[ENGLISH])


def wav(text, path):
    """SPEECH WRITTEN DOWN INSTEAD OF PLAYED, FOR AN ANSWER THAT HAS TO TRAVEL."""
    speech = build()
    samples = speech.say(text)

    if samples is None or not len(samples):
        return None

    path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(path), "wb") as file:
        file.setnchannels(CHANNELS)
        file.setsampwidth(WIDTH_BYTES)
        file.setframerate(speech.rate)
        file.writeframes((np.clip(samples, -1.0, 1.0) * FULL).astype(np.int16).tobytes())

    return path
