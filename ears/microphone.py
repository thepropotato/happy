"""MICROPHONE CAPTURE."""

import collections
import threading
import time
import wave
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd

from face import show
from memory import settings

SAMPLE_RATE = 16000  # WHAT WHISPER WANTS, SO NO RESAMPLING LATER.
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2
BLOCK_SIZE = 1600  # 100 ms.

# THE LONGEST LEAD IN ANYONE CAN ASK FOR, SO THE SETTING MOVES WITHOUT REOPENING THE DEVICE.
MOST_PREROLL_SECONDS = 1.5

FULL_SCALE = 32768.0  # int16, SO LOUDNESS COMES BACK AS 0 TO 1.

RECORDINGS = Path(__file__).resolve().parent.parent / "recordings"


class Recorder:
    def __init__(self, recordings=RECORDINGS):
        self.recordings = Path(recordings)
        self.chunks = []
        self.capturing = False
        self.started_at = 0.0
        self.lock = threading.Lock()
        self.recent = collections.deque(maxlen=blocks(MOST_PREROLL_SECONDS))
        self.listener = None

        # RAW int16: A SAMPLE PAST ±1.0 IN float32 WOULD WRAP TO THE OPPOSITE SIGN.
        self.stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=BLOCK_SIZE,
            callback=self.on_audio,
        )
        self.stream.start()

    def is_recording(self):
        return self.capturing

    def overhear(self, listener):
        """WHO ELSE GETS EVERY BLOCK, KEPT OR NOT."""
        self.listener = listener

    def start(self):
        wanted = blocks(settings.get("ears.preroll"))

        with self.lock:
            # A KEY IS NEVER PRESSED ON THE FIRST SYLLABLE.
            self.chunks = list(self.recent)[-wanted:] if wanted else []
            self.started_at = time.monotonic()
            self.capturing = True

    def stop(self):
        """THE SAVED PATH, OR None IF THERE WAS NOTHING WORTH SAVING."""
        if not self.capturing:
            return None

        # TIMED, NOT MEASURED OFF THE CLIP, WHICH THE PADDING INFLATES.
        held = time.monotonic() - self.started_at

        time.sleep(settings.get("ears.tail"))

        with self.lock:
            if not self.capturing:
                return None

            self.capturing = False
            pcm = b"".join(self.chunks)
            self.chunks = []

        if held < settings.get("ears.hold") or not pcm:
            return None

        return self.save(pcm)

    def close(self):
        self.capturing = False

        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def on_audio(self, indata, frames, moment, status):
        block = bytes(indata)
        listener = self.listener

        with self.lock:
            self.recent.append(block)

            if self.capturing:  # RE-CHECKED UNDER THE LOCK, stop() MAY HAVE WON.
                self.chunks.append(block)
                keeping = True
            else:
                keeping = False

        if keeping:
            show.level(loudness(block))

        if listener:
            listener(block)

    def save(self, pcm):
        self.recordings.mkdir(parents=True, exist_ok=True)
        path = self.recordings / f"{timestamp()}.wav"

        with wave.open(str(path), "wb") as file:
            file.setnchannels(CHANNELS)
            file.setsampwidth(SAMPLE_WIDTH_BYTES)
            file.setframerate(SAMPLE_RATE)
            file.writeframes(pcm)

        return path


def blocks(seconds):
    return int(seconds * SAMPLE_RATE / BLOCK_SIZE)


def loudness(block):
    """HOW LOUD THIS BLOCK WAS, 0 TO 1. MEAN, NOT PEAK, SO IT DOES NOT FLICKER."""
    samples = np.frombuffer(block, dtype=np.int16)

    return float(np.abs(samples).mean()) / FULL_SCALE if samples.size else 0.0


def timestamp():
    # BIGGEST UNIT FIRST, SO SORTING BY NAME IS SORTING BY TIME.
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]
