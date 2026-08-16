"""MICROPHONE CAPTURE."""

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

DEVICE = "ears.microphone"

# WHAT THE SETTING HOLDS WHILE NOBODY HAS PICKED ONE.
ANY = "Whatever the system picks"

FULL_SCALE = 32768.0  # int16, SO LOUDNESS COMES BACK AS 0 TO 1.

RECORDINGS = Path(__file__).resolve().parent.parent / "recordings"


class Recorder:
    """THE DEVICE, OPENED FOR ONE TAKE AND SHUT AFTER IT.

    NOTHING IS HEARD BETWEEN TAKES: THE KEY IS THE ONLY WAY IN, SO A STREAM LEFT RUNNING
    WOULD BE COSTING BATTERY AND HOLDING THE SYSTEM'S MICROPHONE LIGHT ON FOR NOBODY."""

    def __init__(self, recordings=RECORDINGS):
        self.recordings = Path(recordings)
        self.chunks = []
        self.capturing = False
        self.started_at = 0.0
        self.lock = threading.Lock()

        self.empty = False  # THE LAST TAKE WAS NOTHING BUT ZEROS.

        self.stream = None
        self.wanted = None
        self.name = ANY

    def open(self):
        """THE DEVICE THE SETTINGS NAME, OR WHATEVER THE SYSTEM PICKS WHEN THAT ONE IS GONE."""
        self.wanted = settings.get(DEVICE)

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

                # WHILE IT IS OPEN, WHICH IS THE ONLY TIME THE SYSTEM WILL ANSWER.
                self.name = self.naming()

                return
            except Exception as error:
                if device is None:
                    raise

                show.trouble(f"{self.wanted} would not open, hearing on the usual one ({error})")

    def deaf(self):
        """TRUE WHEN THE LAST TAKE WAS DIGITAL SILENCE, WHICH NO ROOM EVER IS."""
        return self.empty

    def hearing(self):
        """THE DEVICE THAT WAS LISTENED TO, BY NAME, WHETHER OR NOT IT IS STILL OPEN."""
        return self.name

    def naming(self):
        try:
            return sd.query_devices(self.stream.device)["name"]
        except Exception:
            return self.wanted or ANY

    def is_recording(self):
        return self.capturing

    def start(self):
        """OPEN THE DEVICE AND KEEP EVERYTHING IT HANDS OVER."""
        self.open()  # AFTER THE SETTING IS READ, SO A MICROPHONE PICKED SINCE LAST TIME IS USED.

        with self.lock:
            self.chunks = []
            self.started_at = time.monotonic()
            self.capturing = True

    def stop(self):
        """THE SAVED PATH, OR None IF THERE WAS NOTHING WORTH SAVING."""
        if not self.capturing:
            return None

        # TIMED, NOT MEASURED OFF THE CLIP, WHICH THE PADDING INFLATES.
        held = time.monotonic() - self.started_at

        time.sleep(settings.get("ears.tail"))  # BEFORE THE CLOSE, OR THERE IS NO TAIL TO KEEP.

        with self.lock:
            if not self.capturing:
                return None

            self.capturing = False
            pcm = b"".join(self.chunks)
            self.chunks = []

        self.close()

        # ZEROS ARE NOT A QUIET ROOM, THEY ARE A DEVICE THAT HAS STOPPED HEARING ALTOGETHER.
        self.empty = bool(pcm) and not any(pcm)

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

        with self.lock:
            if not self.capturing:  # RE-CHECKED UNDER THE LOCK, stop() MAY HAVE WON.
                return

            self.chunks.append(block)

        show.level(loudness(block))

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


def loudness(block):
    """HOW LOUD THIS BLOCK WAS, 0 TO 1. MEAN, NOT PEAK, SO IT DOES NOT FLICKER."""
    samples = np.frombuffer(block, dtype=np.int16)

    return float(np.abs(samples).mean()) / FULL_SCALE if samples.size else 0.0


def timestamp():
    # BIGGEST UNIT FIRST, SO SORTING BY NAME IS SORTING BY TIME.
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]
