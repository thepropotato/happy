"""WHERE SPEAKING HAPPENS."""

from voice.engines import VoiceError, attempt, chosen, installed, names
from voice.mute import Mute
from voice.speaker import Speaker

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
