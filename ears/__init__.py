"""WHERE HEARING HAPPENS: THE KEY, THE MICROPHONE, THE WORDS."""

from ears.microphone import Recorder
from ears.trigger import PushToTalk

__all__ = ["PushToTalk", "Recorder", "load_model", "transcribe"]


def load_model():
    """IMPORTED LATE, SO NOTHING PAYS FOR WHISPERX UNTIL IT IS WANTED."""
    from ears import transcribing

    return transcribing.load_model()


def transcribe(audio_file):
    from ears import transcribing

    return transcribing.transcribe(audio_file)
