"""WHERE SPEAKING HAPPENS."""

import wave

import numpy as np

from voice.engines import VoiceError, attempt, build, chosen, installed, names
from voice.mute import Mute
from voice.speaker import Speaker

CHANNELS = 1
WIDTH_BYTES = 2
FULL = 32767

__all__ = [
    "Mute",
    "Speaker",
    "VoiceError",
    "attempt",
    "chosen",
    "create",
    "installed",
    "names",
]


def create(**kwargs):
    """A SPEAKER, PLUS THE REASON IT IS MUTE WHEN IT IS."""
    voice, why = attempt(**kwargs)

    return Speaker(voice), why


def wav(text, path):
    """SPEECH WRITTEN DOWN INSTEAD OF PLAYED, FOR AN ANSWER THAT HAS TO TRAVEL.

    ITS OWN VOICE, NOT THE SPEAKER'S: THE SPEAKER MAY STILL BE HALFWAY THROUGH
    SAYING SOMETHING IN THE ROOM, AND ONE MODEL CANNOT DO BOTH AT ONCE.
    """
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
