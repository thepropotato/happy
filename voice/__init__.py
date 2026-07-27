"""WHERE SPEAKING HAPPENS."""

from voice.piper import MODELS, SUFFIX, Mute, Voice, VoiceError
from voice.speaker import Speaker

__all__ = ["MODELS", "Mute", "SUFFIX", "Speaker", "Voice", "VoiceError", "create"]


def create(**kwargs):
    """A SPEAKER, PLUS THE REASON IT IS MUTE WHEN IT IS.

    CATCHES EVERYTHING ON PURPOSE. LOSING THE VOICE IS NOT A REASON TO LOSE THE
    ASSISTANT: HAPPY GOES BACK TO ANSWERING IN WRITING.
    """
    try:
        return Speaker(Voice(**kwargs)), None
    except Exception as error:
        return Speaker(Mute()), f"{error}"
