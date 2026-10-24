"""Happy's voice: Kyutai Pocket TTS, streamed sentence by sentence and cut off the moment someone talks over it."""

import collections
import logging
import queue
import sys
import threading
import time

import numpy as np
import sounddevice as sd

from happy import paths
from happy.speech.spoken_text import speakable

log = logging.getLogger("happy.speaker")


def chime(rate, rising=True):
    """A short soft two-note blip, so a wake-up is heard as well as seen."""
    notes = (660, 990) if rising else (880, 587)
    parts = []
    for freq in notes:
        t = np.arange(int(rate * 0.07)) / rate
        envelope = np.sin(np.pi * t / t[-1]) ** 2
        parts.append(0.12 * envelope * np.sin(2 * np.pi * freq * t))
    return np.concatenate(parts).astype(np.float32)


def reload_devices():
    sd._terminate()
    sd._initialize()


class Speaker:
    def __init__(self, voice="alba", on_level=None, on_speaking=None, refresh_devices=None):
        self.voice = voice
        self.on_level = on_level or (lambda level: None)
        self.on_speaking = on_speaking or (lambda speaking: None)
        self.refresh_devices = refresh_devices or reload_devices
        self.texts = queue.Queue()
        self.audio = collections.deque()
        self.audio_lock = threading.Lock()
        self.cut = threading.Event()
        self.busy = 0
        self.busy_lock = threading.Lock()
        self.stream = None
        self.last_sound = 0.0
        self.speaking = False
        self.chime_until = 0.0

    def warm(self):
        """Downloads and prepares the voice without starting to play anything."""
        from pocket_tts import TTSModel

        self.model = TTSModel.load_model()
        self.rate = self.model.sample_rate
        self.state = self.voice_state(self.voice)

    def start(self):
        started = time.monotonic()
        self.warm()
        log.info("voice ready in %.1fs", time.monotonic() - started)
        threading.Thread(target=self.synthesise, name="voice", daemon=True).start()
        threading.Thread(target=self.housekeep, name="voice-out", daemon=True).start()

    def voice_state(self, voice):
        from pocket_tts.models.model_state import export_model_state

        cached = paths.MODELS / "voices" / f"{voice}.safetensors"
        if cached.exists():
            return self.model.get_state_for_audio_prompt(cached)
        state = self.model.get_state_for_audio_prompt(voice)
        cached.parent.mkdir(parents=True, exist_ok=True)
        export_model_state(state, cached)
        return state

    def say(self, text):
        """Queues a sentence to be spoken; returns what will actually be said."""
        spoken = speakable(text)
        if spoken and any(c.isalnum() for c in spoken):
            log.info("saying: %s", spoken)
            with self.busy_lock:
                self.busy += 1
            self.texts.put(spoken)
        return spoken

    def blip(self, rising=True):
        """The wake chime; it is not Happy talking, so it never changes the face or deafens the microphone."""
        sound = chime(self.rate, rising)
        self.chime_until = time.monotonic() + len(sound) / self.rate + 0.2
        self.play(sound)

    def stop(self):
        """Stops talking now, dropping anything not yet said."""
        self.cut.set()
        while not self.texts.empty():
            try:
                self.texts.get_nowait()
                with self.busy_lock:
                    self.busy -= 1
            except queue.Empty:
                break
        with self.audio_lock:
            self.audio.clear()

    def idle(self):
        with self.audio_lock:
            pending = bool(self.audio)
        return self.busy <= 0 and not pending

    def wait(self, timeout=60.0):
        ends = time.monotonic() + timeout
        while not self.idle() and time.monotonic() < ends:
            time.sleep(0.05)

    def synthesise(self):
        while True:
            text = self.texts.get()
            self.cut.clear()
            try:
                for chunk in self.model.generate_audio_stream(self.state, text, stop=self.cut):
                    if self.cut.is_set():
                        break
                    self.play(chunk.numpy().astype(np.float32))
            except Exception:
                log.exception("could not say %r", text)
            finally:
                with self.busy_lock:
                    self.busy -= 1

    def play(self, samples):
        with self.audio_lock:
            self.audio.append(samples)
        self.ensure_stream()

    def ensure_stream(self):
        if self.stream is not None:
            return
        self.follow_output()
        try:
            self.stream = sd.OutputStream(samplerate=self.rate, channels=1, dtype="float32",
                                          blocksize=int(self.rate * 0.03), callback=self.fill)
            self.stream.start()
            log.info("speaking through %s", sd.query_devices(kind="output")["name"])
        except Exception:
            log.exception("no speaker to play through")
            self.stream = None

    def follow_output(self):
        """The sound library learns the devices once; if the output changed since (headphones in or out), it learns them again."""
        if sys.platform != "darwin":
            return
        try:
            from happy.system import macos

            now = macos.output_device()
            known = sd.query_devices(kind="output")["name"]
        except Exception:
            return
        if now and now != known:
            log.info("the output moved from %s to %s; reloading the sound devices", known, now)
            self.refresh_devices()

    def fill(self, out, frames, timing, status):
        written = 0
        with self.audio_lock:
            while written < frames and self.audio:
                head = self.audio[0]
                take = min(frames - written, len(head))
                out[written:written + take, 0] = head[:take]
                written += take
                if take == len(head):
                    self.audio.popleft()
                else:
                    self.audio[0] = head[take:]
        out[written:, 0] = 0
        if written:
            self.last_sound = time.monotonic()
        self.on_level(float(np.sqrt(np.mean(out[:, 0] ** 2))) if written else 0.0)

    def housekeep(self):
        """Tells the face when talking starts and stops, and lets the speaker go when quiet."""
        while True:
            time.sleep(0.05)
            now = time.monotonic()
            talking = self.busy > 0 or (not self.idle() or now - self.last_sound < 0.15) and now > self.chime_until
            if talking != self.speaking:
                self.speaking = talking
                self.on_speaking(talking)
            if self.stream is not None and self.idle() and now - self.last_sound > 2.0:
                try:
                    self.stream.stop()
                    self.stream.close()
                finally:
                    self.stream = None
