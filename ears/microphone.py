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

BLOCK_SECONDS = BLOCK_SIZE / SAMPLE_RATE

DEVICE = "ears.microphone"

# WHAT THE SETTING HOLDS WHILE NOBODY HAS PICKED ONE.
ANY = "Whatever the system picks"

# A DEAD DEVICE STILL HANDS OVER BLOCKS ON TIME, SO ONLY THEIR BEING EMPTY GIVES IT AWAY, AND
# A FEW SECONDS OF IT IS LONGER THAN ANY REAL ROOM IS EVER PERFECTLY SILENT.
DEAF_SECONDS = 5

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

        # HOW LONG THE DEVICE HAS BEEN HANDING OVER NOTHING BUT ZEROS.
        self.empty = 0.0

        self.stream = None
        self.wanted = None
        self.open()

    def open(self):
        """THE DEVICE THE SETTINGS NAME, OR WHATEVER THE SYSTEM PICKS WHEN THAT ONE IS GONE."""
        self.wanted = settings.get(DEVICE)
        self.empty = 0.0

        for device in (named(self.wanted), None):
            try:
                # RAW int16: A SAMPLE PAST ±1.0 IN float32 WOULD WRAP TO THE OPPOSITE SIGN.
                self.stream = sd.RawInputStream(
                    device=device,
                    samplerate=SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype="int16",
                    blocksize=BLOCK_SIZE,
                    callback=self.on_audio,
                )
                self.stream.start()

                return
            except Exception as error:
                if device is None:
                    raise

                show.trouble(f"{self.wanted} would not open, hearing on the usual one ({error})")

    def refit(self):
        """A DIFFERENT MICROPHONE WAS PICKED. A STREAM CANNOT BE RETUNED, ONLY REPLACED."""
        if settings.get(DEVICE) == self.wanted or self.capturing:
            return

        self.close()
        self.open()

    def deaf(self):
        """TRUE WHEN THE DEVICE IS HANDING OVER DIGITAL SILENCE, WHICH NO ROOM EVER IS."""
        return self.empty >= DEAF_SECONDS

    def hearing(self):
        """THE DEVICE BEING LISTENED TO, BY NAME."""
        try:
            return sd.query_devices(self.stream.device)["name"]
        except Exception:
            return self.wanted or ANY

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

    def peek(self, where):
        """THE TAKE AS FAR AS IT HAS GOT, ON DISK, WITHOUT ENDING IT."""
        with self.lock:
            pcm = b"".join(self.chunks) if self.capturing else b""

        return written(where, pcm) if pcm else None

    def close(self):
        self.capturing = False

        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def on_audio(self, indata, frames, moment, status):
        block = bytes(indata)
        listener = self.listener

        # ZEROS ARE NOT A QUIET ROOM, THEY ARE A DEVICE THAT HAS STOPPED HEARING ALTOGETHER.
        self.empty = 0.0 if any(block) else self.empty + frames / SAMPLE_RATE

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

        return written(self.recordings / f"{timestamp()}.wav", pcm)


def written(where, pcm):
    """SOUND ONTO DISK AS THE ONE SHAPE EVERYTHING HERE READS."""
    with wave.open(str(where), "wb") as file:
        file.setnchannels(CHANNELS)
        file.setsampwidth(SAMPLE_WIDTH_BYTES)
        file.setframerate(SAMPLE_RATE)
        file.writeframes(pcm)

    return where


def offered():
    """EVERY DEVICE THAT CAN HEAR, BY NAME."""
    try:
        found = [each["name"] for each in sd.query_devices() if each["max_input_channels"] > 0]
    except Exception:
        found = []

    return [ANY] + found


def named(wanted):
    """ONE DEVICE'S INDEX, OR None FOR WHATEVER THE SYSTEM PICKS."""
    if not wanted or wanted == ANY:
        return None

    try:
        for index, each in enumerate(sd.query_devices()):
            if each["name"] == wanted and each["max_input_channels"] > 0:
                return index
    except Exception:
        pass

    return None


def blocks(seconds):
    return int(seconds * SAMPLE_RATE / BLOCK_SIZE)


def loudness(block):
    """HOW LOUD THIS BLOCK WAS, 0 TO 1. MEAN, NOT PEAK, SO IT DOES NOT FLICKER."""
    samples = np.frombuffer(block, dtype=np.int16)

    return float(np.abs(samples).mean()) / FULL_SCALE if samples.size else 0.0


def timestamp():
    # BIGGEST UNIT FIRST, SO SORTING BY NAME IS SORTING BY TIME.
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]
