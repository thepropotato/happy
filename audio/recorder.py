"""
MICROPHONE CAPTURE. START ON PUSH, STOP ON RELEASE, ONE WAV FILE PER TAKE.

THE INPUT STREAM STAYS OPEN FOR THE LIFE OF THE PROCESS AND start()/stop() JUST
GATE WHETHER THE CALLBACK KEEPS WHAT IT HEARS. OPENING A DEVICE COSTS ROUGHLY A
TENTH OF A SECOND, WHICH IS ENOUGH TO SWALLOW THE FIRST WORD IF IT HAPPENED ON
EVERY KEY PRESS.
"""

import collections
import threading
import time
import wave
from datetime import datetime
from pathlib import Path

import sounddevice as sd

SAMPLE_RATE = 16000  # WHAT WHISPER WANTS, SO NO RESAMPLING LATER.
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2  # int16
BLOCK_SIZE = 1600  # 100 ms.
MIN_HELD_SECONDS = 0.25  # A KEY HELD BRIEFER THAN THIS WAS BRUSHED, NOT SPOKEN OVER.

# A KEY IS NEVER PRESSED EXACTLY ON THE FIRST SYLLABLE OR HELD PAST THE LAST
# ONE, AND WHISPER TRANSCRIBES A WORD CUT AT THE EDGE OF A CLIP NOTICEABLY
# WORSE. SO EVERY TAKE IS PADDED AT BOTH ENDS.
PREROLL_SECONDS = 0.3
TAIL_SECONDS = 0.2

RECORDINGS_DIR = Path(__file__).resolve().parent.parent / "recordings"


class Recorder:
    def __init__(self, recordings_dir=RECORDINGS_DIR):
        self.recordings_dir = Path(recordings_dir)
        self.chunks = []
        self.capturing = False
        self.started_at = 0.0
        self.lock = threading.Lock()
        self.recent = collections.deque(maxlen=int(PREROLL_SECONDS * SAMPLE_RATE / BLOCK_SIZE))

        # RAW int16 STRAIGHT FROM PORTAUDIO. GOING VIA float32 WOULD MEAN
        # CONVERTING BY HAND, AND A SAMPLE PAST +-1.0 WRAPS TO THE OPPOSITE SIGN.
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

    def start(self):
        with self.lock:
            self.chunks = list(self.recent)  # THE MOMENT BEFORE THE KEY WENT DOWN.
            self.started_at = time.monotonic()
            self.capturing = True

    def stop(self):  # RETURNS THE SAVED PATH, OR NONE IF THERE WAS NOTHING WORTH SAVING.
        if not self.capturing:
            return None

        # TIMED, NOT MEASURED OFF THE CLIP, WHICH THE PADDING ALWAYS INFLATES.
        held = time.monotonic() - self.started_at

        time.sleep(TAIL_SECONDS)  # STILL RECORDING, TO CATCH THE LAST WORD.

        with self.lock:
            if not self.capturing:
                return None

            self.capturing = False
            pcm = b"".join(self.chunks)
            self.chunks = []

        if held < MIN_HELD_SECONDS or not pcm:
            return None

        return self.save(pcm)

    def close(self):
        self.capturing = False

        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def on_audio(self, indata, frames, time_info, status):  # THE AUDIO THREAD CALLS THIS.
        block = bytes(indata)

        with self.lock:
            self.recent.append(block)

            if self.capturing:  # RE-CHECKED UNDER THE LOCK, stop() MAY HAVE JUST WON.
                self.chunks.append(block)

    def save(self, pcm):
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        path = self.recordings_dir / f"{timestamp()}.wav"

        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(SAMPLE_WIDTH_BYTES)
            wav_file.setframerate(SAMPLE_RATE)
            wav_file.writeframes(pcm)

        return path


def timestamp():
    # BIGGEST UNIT FIRST AND ZERO PADDED, SO SORTING BY NAME IS SORTING BY TIME.
    # MILLISECONDS KEEP TWO QUICK TAKES FROM COLLIDING.
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]
