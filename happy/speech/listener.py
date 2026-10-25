"""The microphone, turned into requests: by name, by holding a key, or as a follow-up."""

import collections
import logging
import queue
import re
import sys
import threading
import time

import numpy as np
import sherpa_onnx
import sounddevice as sd

from happy.speech import models
from happy.speech.transcriber import Transcriber
from happy.speech.addressing import addressed, mentions, sounds_like

RATE = 16000
BLOCK = 1600
PREROLL = 2.5
PEEKS = (1.4, 1.8, 2.2, 2.6, 3.0, 3.5)
TRAILING_SILENCE = 0.8
LONGEST = 20.0
TAP = 0.35

log = logging.getLogger("happy.listener")


def pick_mic(wanted=""):
    """The named mic, else whichever one the system is set to, headphones included."""
    devices = [(i, d) for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0]
    if wanted:
        for i, d in devices:
            if wanted.lower() in d["name"].lower():
                return i, d["name"]
    default = sd.default.device[0]
    for i, d in devices:
        if i == default:
            return i, d["name"]
    return (devices[0][0], devices[0][1]["name"]) if devices else (None, "none")


FILLERS = {"um", "uh", "hmm", "mm", "mhm", "ah", "oh", "er", "erm", "huh", "the", "a"}


# SAID OVER HAPPY, THESE ONLY MEAN "BE QUIET"; THEY ARE NOT A NEW REQUEST.
STOPS = {"stop", "wait", "quiet", "enough", "cancel", "never mind", "nevermind", "shut up", "hold on", "be quiet", "stop talking", "ok stop", "okay stop"}


def after_name(text, name):
    """What follows the name when it opens what was said over Happy, or None when the name is not among the first words."""
    if not mentions(text, name):
        return None
    command = addressed(text, name)
    if command is not None:
        return command
    words = re.findall(r"[\w']+", text)
    first = next(w for w in words[:3] if sounds_like(w, name))
    return text.split(first, 1)[1].lstrip(" ,.!?;:-").strip()


def real_words(text):
    """Whether a transcript is somebody saying something rather than a cough, a creak or a breath."""
    words = [w for w in re.findall(r"[a-z']+", (text or "").lower()) if w not in FILLERS]
    return len(words) >= 2 or (len(words) == 1 and len(words[0]) >= 3)


def looping(text):
    """Whether the recognizer got stuck repeating itself on noise, like "I'm sorry." eight times while nobody spoke."""
    parts = [" ".join(re.findall(r"[a-z']+", part.lower())) for part in re.split(r"[.!?,;]+", text or "")]
    counts = collections.Counter(part for part in parts if len(part.split()) >= 2)
    return any(count >= 3 for count in counts.values())


class Endpoint:
    """Decides when someone has finished speaking, counting audio rather than wall-clock time."""

    def __init__(self, wait=6.0):
        config = sherpa_onnx.VadModelConfig()
        config.silero_vad.model = str(models.ensure(["vad"])["vad"])
        config.silero_vad.threshold = 0.35
        config.silero_vad.min_silence_duration = 0.3
        config.silero_vad.min_speech_duration = 0.1
        config.sample_rate = RATE
        self.vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=LONGEST + 10)
        self.wait = wait
        self.started = None
        self.last_speech = None
        self.heard = 0.0

    def feed(self, samples):
        """Returns 'more', 'done' or 'nothing'."""
        self.vad.accept_waveform(samples)
        self.heard += len(samples) / RATE
        if self.vad.is_speech_detected():
            self.started = self.heard if self.started is None else self.started
            self.last_speech = self.heard
        while not self.vad.empty():
            self.vad.pop()
        if self.started is None:
            return "nothing" if self.heard > self.wait else "more"
        if self.heard - self.last_speech > TRAILING_SILENCE or self.heard - self.started > LONGEST:
            return "done"
        return "more"


class Listener:
    """Listens all the time, but only speech that starts by addressing Happy by name goes anywhere."""

    def __init__(self, name, wake=True, device="", on_heard=None, on_state=None, on_level=None, echo_cancel=True,
                 on_barge=None, echo=None, refresh_devices=None):
        self.name = name
        self.refresh_devices = refresh_devices or self.reopen
        self.opened_on = ""
        self.on_barge = on_barge or (lambda: None)
        self.echo = echo or (lambda text: False)
        self.barging = False
        self.barged = False
        self.echo_cancel = echo_cancel
        self.stream = None
        self.mic = None
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
        self.segment = None
        self.peeks = list(PEEKS)
        self.woken = False
        self.key_down_at = None
        self.deaf = threading.Event()
        self.stopping = threading.Event()
        self.lock = threading.Lock()
        self.zeros = 0.0
        self.warned = False

    def start(self):
        self.stt = Transcriber()
        self.segment = Endpoint(wait=float("inf"))
        self.open_mic()
        self.worker = threading.Thread(target=self.run, name="ears", daemon=True)
        self.worker.start()
        if sys.platform == "darwin":
            threading.Thread(target=self.follow_input, name="microphone follower", daemon=True).start()

    def follow_input(self):
        """Moves to the system's microphone when it changes (headphones in or out), unless one is named in settings."""
        from happy.system import macos

        while not self.stopping.wait(1.0):
            if self.device:
                continue
            try:
                now = macos.input_device()
            except Exception:
                continue
            if now and self.opened_on and now != self.opened_on:
                log.info("the microphone moved from %s to %s; reopening it", self.opened_on, now)
                self.opened_on = now
                try:
                    self.refresh_devices() if self.stream is not None else self.reopen()
                except Exception:
                    log.exception("the microphone would not reopen on %s", now)

    def open_mic(self):
        """Echo-cancelled on macOS, so a video playing is not taken for the person talking; a plain stream elsewhere."""
        self.stream = None
        self.mic = None
        if sys.platform == "darwin":
            from happy.system import macos

            try:
                self.opened_on = macos.input_device()
            except Exception:
                self.opened_on = ""
        if sys.platform == "darwin" and self.echo_cancel and not self.device:
            from happy.speech.microphone import EchoCancelled

            try:
                self.mic = EchoCancelled(self.blocks.put)
                self.mic.start()
                self.mic_name = f"{self.opened_on or 'the default microphone'}, with echo cancellation"
                log.info("listening on %s", self.mic_name)
                return
            except Exception:
                log.exception("echo cancellation is not available; listening without it")
                self.mic = None
        index, self.mic_name = pick_mic(self.device)
        self.stream = sd.InputStream(samplerate=RATE, channels=1, dtype="float32", blocksize=BLOCK,
                                     device=index, callback=self.arrived)
        self.stream.start()
        log.info("listening on %s", self.mic_name)

    def close_mic(self):
        try:
            if self.mic is not None:
                self.mic.stop()
            if self.stream is not None:
                self.stream.stop()
                self.stream.close()
        except Exception:
            pass

    def reopen(self):
        """Opens the microphone again, after the sound devices were reloaded underneath it."""
        self.close_mic()
        self.open_mic()

    def stop(self):
        self.stopping.set()
        self.close_mic()

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

    def listen_now(self, wait=6.0, announce=True):
        """Opens the mic for an answer without needing the name again; quietly when Happy opened it himself."""
        with self.lock:
            if self.mode not in ("idle", "ignoring"):
                return
            self.capture = []
            self.endpoint = Endpoint(wait=wait)
            self.mode = "follow"
        self.on_state("listening" if announce is True else "following")

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
            if mode in ("key", "follow"):
                self.on_level(float(np.sqrt(np.mean(block ** 2))))
            if mode in ("idle", "ignoring"):
                self.overhear(block, mode)
                continue
            audio, how = None, mode
            with self.lock:
                self.capture.append(block)
                if self.mode == "finishing":
                    audio, how = np.concatenate(self.capture), "key"
                    self.mode, self.capture = "idle", []
                elif self.mode == "follow":
                    verdict = self.endpoint.feed(block)
                    if verdict == "more":
                        continue
                    audio = np.concatenate(self.capture) if verdict == "done" else None
                    self.mode, self.capture = "idle", []
                else:
                    continue
            self.fresh_segment()
            if audio is None:
                self.on_state("idle")
                continue
            self.finish(audio, how)

    def fresh_segment(self):
        self.segment = Endpoint(wait=float("inf"))
        self.peeks = list(PEEKS)
        self.woken = False
        self.barged = False

    def overhear(self, block, mode):
        """Follows speech in the room: the name wakes Happy the moment it is said, and while Happy is
        talking, real words from the person cut him off. Barging in needs echo cancellation, or Happy
        would cut himself off with his own voice."""
        self.ring.append(block)
        speaking = self.deaf.is_set()
        barge = speaking and self.mic is not None
        if barge != self.barging and not self.woken:
            self.barging = barge
            if self.segment.started is not None:
                self.fresh_segment()
                self.capture = []
                with self.lock:
                    if self.mode == "ignoring":
                        self.mode = "idle"
                        mode = "idle"
        if (speaking and not barge) or (not self.wake_enabled and not self.barging):
            if self.segment.started is not None:
                self.fresh_segment()
                self.capture = []
            return
        verdict = self.segment.feed(block)
        if mode == "ignoring":
            if verdict == "done":
                with self.lock:
                    self.mode = "idle"
                self.fresh_segment()
            return
        if self.segment.started is None:
            return
        if not self.capture:
            self.capture = list(self.ring)[-10:]
        else:
            self.capture.append(block)
        if verdict == "done":
            audio = np.concatenate(self.capture)
            how = "barge" if self.barged or self.barging else "woken" if self.woken else "overheard"
            self.capture = []
            self.fresh_segment()
            self.barging = self.deaf.is_set() and self.mic is not None
            self.finish(audio, how)
        elif not self.woken and self.peeks and len(self.capture) * BLOCK / RATE >= self.peeks[0]:
            self.peeks.pop(0)
            opening = self.stt(np.concatenate(self.capture))
            if self.barging:
                # LEAKED ECHO TRANSCRIBES AS OTHER WORDS THAN HAPPY SAID, SO ONLY HIS NAME, WHICH HE NEVER SAYS, CUTS HIM OFF.
                if real_words(opening) and not self.echo(opening) and mentions(opening, self.name):
                    self.woken = self.barged = True
                    log.info("barged in: %r", opening)
                    self.on_barge()
                elif not self.peeks:
                    with self.lock:
                        self.mode = "ignoring"
                    self.capture = []
                return
            if addressed(opening, self.name) is not None:
                self.woken = True
                self.on_state("listening")
            elif (len(opening.split()) >= 3 and not mentions(opening, self.name)) or not self.peeks and not mentions(opening, self.name):
                with self.lock:
                    self.mode = "ignoring"
                self.capture = []

    def finish(self, audio, how):
        if how != "overheard":
            self.on_state("transcribing")
        text = self.stt(audio)
        if looping(text):
            log.info("heard a loop, not words; dropped (%s): %r", how, text)
            if how != "overheard":
                self.on_state("missed")
            return
        if how == "barge":
            command = after_name(text, self.name)
            if not real_words(text) or self.echo(text) or command is None:
                self.on_state("missed")
                return
            log.info("heard (barge): %r", text)
            if self.deaf.is_set():
                self.on_barge()
            if re.sub(r"[^a-z ]", "", command.lower()).strip() in STOPS:
                self.on_state("missed")
            elif command:
                self.on_heard(command, "barge")
            else:
                self.listen_now()
            return
        if how in ("overheard", "woken"):
            command = addressed(text, self.name)
            if command is None:
                if how == "woken":
                    self.on_state("idle")
                return
            log.info("heard: %r", text)
            if not command:
                self.listen_now(announce=how == "overheard")
                return
            self.on_heard(command, "wake")
            return
        log.info("heard (%s): %r", how, text)
        if not text or how == "follow" and not real_words(text):
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
