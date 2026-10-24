"""The microphone, turned into requests: by name, by holding a key, or as a follow-up."""

import collections
import logging
import queue
import threading
import time

import numpy as np
import sherpa_onnx
import sounddevice as sd

from happy import models
from happy.ears.stt import Transcriber
from happy.ears.wake import WakeWord, addressed

RATE = 16000
BLOCK = 1600
PREROLL = 2.5
TRAILING_SILENCE = 0.8
LONGEST = 20.0
TAP = 0.35

log = logging.getLogger("happy.ears")


def pick_mic(wanted=""):
    """The built-in mic unless one is named, so Bluetooth headphones stay in their good audio mode."""
    devices = [(i, d) for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0]
    if wanted:
        for i, d in devices:
            if wanted.lower() in d["name"].lower():
                return i, d["name"]
    for i, d in devices:
        name = d["name"].lower()
        if ("macbook" in name or "built-in" in name or "internal" in name) and "microphone" in name:
            return i, d["name"]
    default = sd.default.device[0]
    for i, d in devices:
        if i == default:
            return i, d["name"]
    return (devices[0][0], devices[0][1]["name"]) if devices else (None, "none")


class Endpoint:
    """Decides when someone has finished speaking."""

    def __init__(self, wait=6.0):
        config = sherpa_onnx.VadModelConfig()
        config.silero_vad.model = str(models.ensure(["vad"])["vad"])
        config.silero_vad.threshold = 0.5
        config.silero_vad.min_silence_duration = 0.3
        config.silero_vad.min_speech_duration = 0.15
        config.sample_rate = RATE
        self.vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=LONGEST + 10)
        self.wait = wait
        self.started = None
        self.last_speech = None
        self.began = time.monotonic()
        self.heard = 0.0

    def feed(self, samples):
        """Returns 'more', 'done' or 'nothing'."""
        self.vad.accept_waveform(samples)
        now = time.monotonic()
        self.heard += len(samples) / RATE
        if self.vad.is_speech_detected():
            self.started = self.started or now
            self.last_speech = now
        while not self.vad.empty():
            self.vad.pop()
        if self.started is None:
            return "nothing" if now - self.began > self.wait else "more"
        if now - self.last_speech > TRAILING_SILENCE or self.heard > LONGEST:
            return "done"
        return "more"


class Ears:
    def __init__(self, name, wake=True, device="", on_heard=None, on_state=None, on_level=None):
        self.name = name
        self.wake_enabled = wake
        self.device = device
        self.on_heard = on_heard or (lambda text, how: None)
        self.on_state = on_state or (lambda state: None)
        self.on_level = on_level or (lambda level: None)
        self.blocks = queue.Queue()
        self.ring = collections.deque(maxlen=int(PREROLL * RATE / BLOCK))
        self.mode = "idle"
        self.capture = []
        self.endpoint = None
        self.key_down_at = None
        self.deaf = threading.Event()
        self.stopping = threading.Event()
        self.lock = threading.Lock()
        self.zeros = 0.0
        self.warned = False

    def start(self):
        self.stt = Transcriber()
        self.wake = WakeWord(self.name, threshold=0.05, boost=3.0) if self.wake_enabled else None
        index, self.mic_name = pick_mic(self.device)
        log.info("listening on %s", self.mic_name)
        self.stream = sd.InputStream(samplerate=RATE, channels=1, dtype="float32", blocksize=BLOCK,
                                     device=index, callback=self.arrived)
        self.stream.start()
        self.worker = threading.Thread(target=self.run, name="ears", daemon=True)
        self.worker.start()

    def stop(self):
        self.stopping.set()
        try:
            self.stream.stop()
            self.stream.close()
        except Exception:
            pass

    def arrived(self, data, frames, timing, status):
        self.blocks.put(data[:, 0].copy())

    def mute_wake(self, muted):
        """Stops the name being heard in Happy's own voice while it talks."""
        if muted:
            self.deaf.set()
        else:
            self.deaf.clear()

    def key_down(self):
        with self.lock:
            self.key_down_at = time.monotonic()
            self.capture = list(self.ring)[-2:]
            self.mode = "key"
        self.on_state("listening")

    def key_up(self):
        with self.lock:
            if self.mode != "key":
                return
            held = time.monotonic() - (self.key_down_at or time.monotonic())
            if held < TAP:
                self.endpoint = Endpoint(wait=8.0)
                self.mode = "follow"
                return
            self.mode = "finishing"

    def listen_now(self, wait=6.0):
        """Opens the mic for an answer without needing the name again."""
        with self.lock:
            self.capture = []
            self.endpoint = Endpoint(wait=wait)
            self.mode = "follow"
        self.on_state("listening")

    def cancel(self):
        with self.lock:
            self.mode = "idle"
            self.capture = []

    def run(self):
        while not self.stopping.is_set():
            try:
                block = self.blocks.get(timeout=0.2)
            except queue.Empty:
                continue
            self.check_silence(block)
            with self.lock:
                mode = self.mode
            if mode in ("key", "follow", "listening"):
                self.on_level(float(np.sqrt(np.mean(block ** 2))))
            if mode == "idle":
                self.ring.append(block)
                if self.wake and not self.deaf.is_set() and self.wake.feed(block):
                    with self.lock:
                        self.capture = list(self.ring)
                        self.endpoint = Endpoint(wait=3.0)
                        self.mode = "armed"
                continue
            with self.lock:
                self.capture.append(block)
                if self.mode == "finishing":
                    self.mode = "idle"
                    audio = np.concatenate(self.capture)
                    self.capture = []
                    self.finish(audio, "key")
                    continue
                if self.mode in ("armed", "follow", "listening"):
                    verdict = self.endpoint.feed(block)
                    if verdict == "more":
                        continue
                    how = self.mode
                    audio = np.concatenate(self.capture) if verdict == "done" else None
                    self.mode = "idle"
                    self.capture = []
                else:
                    continue
            if audio is None:
                if how != "armed":
                    self.on_state("idle")
                continue
            self.finish(audio, how)

    def finish(self, audio, how):
        if how != "armed":
            self.on_state("transcribing")
        text = self.stt(audio)
        log.info("heard (%s): %r", how, text)
        if how == "armed":
            command = addressed(text, self.name)
            if command is None:
                return
            if not command:
                self.listen_now()
                return
            self.on_heard(command, "wake")
            return
        if not text:
            self.on_state("missed")
            return
        command = addressed(text, self.name)
        self.on_heard(command if command else text, how)

    def check_silence(self, block):
        """Notices a microphone that hands over nothing but zeros."""
        if np.any(block):
            self.zeros = 0.0
            return
        self.zeros += len(block) / RATE
        if self.zeros > 3 and not self.warned:
            self.warned = True
            self.on_state("silent-mic")
