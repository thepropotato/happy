"""WHERE SPEAKING HAPPENS."""

import wave

import numpy as np

from voice.engines import VoiceError, attempt, build, chosen, installed, names
from voice.mute import Mute
from voice.speaker import Speaker

CHANNELS = 1
WIDTH_BYTES = 2
FULL = 32767

SAMPLE = "Hello, I'm Happy. This is what I sound like."

__all__ = [
    "Mute",
    "SAMPLE",
    "Speaker",
    "VoiceError",
    "attempt",
    "chosen",
    "create",
    "installed",
    "names",
    "sample",
]


def create(**kwargs):
    """A SPEAKER, PLUS THE REASON IT IS MUTE WHEN IT IS."""
    voice, why = attempt(**kwargs)

    return Speaker(voice), why


def sample(name=None):
    """THE LINE TO SAY FOR SOMEBODY WHO WANTS TO HEAR A VOICE BEFORE THEY PICK IT."""
    return SAMPLE


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
