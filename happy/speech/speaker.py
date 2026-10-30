"""Happy's voice: Kyutai Pocket TTS, streamed sentence by sentence, paused the moment someone talks over it."""

import collections
import logging
import queue
import sys
import threading
import time

import numpy as np
import sounddevice as sd

from happy import paths
from happy.config import speech_speed
from happy.speech.spoken_text import speakable
from happy.speech.stretch import Stretcher

log = logging.getLogger("happy.speaker")

# A PAUSE LONGER THAN THIS GOES BACK TO THE START OF THE SENTENCE; HALF A WORD AFTER A GAP SOUNDS BROKEN.
REWIND_AFTER = 1.5
# AT A FASTER SPEED A SENTENCE IS PLAYED QUICKER THAN A SLOW COMPUTER MAKES IT, SO IT IS HELD BACK UNTIL ENOUGH IS MADE
# TO PLAY THROUGH WITHOUT RUNNING DRY. SENTENCES LONGER THAN THIS MAY STILL BREAK ONCE NEAR THE END.
LONGEST_SENTENCE = 8.0


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
    def __init__(self, voice="alba", on_level=None, on_speaking=None, refresh_devices=None, device="", speed=1.0):
        self.voice = voice
        self.speed = speech_speed(speed)
        self.stretcher = None
        self.output = np.empty(0, np.float32)
        self.device = device
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
        self.recent = collections.deque(maxlen=4)
        self.lines = {}
        self.made = {}
        self.next_line = 0
        self.playing = None
        self.hold = "playing"
        self.paused_at = 0.0
        self.ramp = None
        self.started = None
        self.pace = None
        self.began = {}

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

    def use_voice(self, voice):
        """Speaks in another voice from the next sentence, loaded aside so nothing waits on it."""
        state = self.voice_state(voice)
        self.voice, self.state = voice, state
        log.info("now speaking as %s", voice)

    def say(self, text):
        """Queues a sentence to be spoken; returns what will actually be said."""
        spoken = speakable(text)
        if spoken and any(c.isalnum() for c in spoken):
            log.info("saying: %s", spoken)
            self.recent.append(spoken)
            with self.busy_lock:
                self.busy += 1
            with self.audio_lock:
                line, self.next_line = self.next_line, self.next_line + 1
                self.lines[line] = text.strip()
            self.texts.put((line, spoken))
        return spoken

    def blip(self, rising=True):
        """The wake chime; it is not Happy talking, so it never changes the face or deafens the microphone."""
        sound = chime(self.rate, rising)
        self.chime_until = time.monotonic() + len(sound) / self.rate + 0.2
        self.play(sound)

    def pause(self):
        """Goes quiet mid-word, keeping the place; what was still to come keeps being made."""
        with self.audio_lock:
            if self.hold == "playing":
                self.hold = "fading"

    def paused(self):
        return self.hold != "playing"

    def resume(self):
        """Carries on from the pause, or from the start of the sentence when the pause was long."""
        with self.audio_lock:
            if self.hold == "playing":
                return
            line = self.playing
            if self.hold == "paused" and time.monotonic() - self.paused_at > REWIND_AFTER and line in self.made:
                rest = [each for each in self.audio if each[0] != line]
                ended = [each for each in self.audio if each[0] == line and each[1] is None]
                self.audio = collections.deque([(line, chunk) for chunk in self.made[line]] + ended + rest)
                self.reset_stretch()
                self.started = None
            self.hold, self.ramp = "playing", "in"

    def stop(self):
        """Stops talking now; returns the sentences not yet heard, the one cut off included, as they were written."""
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
            self.reset_stretch()
            unheard = [self.lines[line] for line in sorted(self.lines)]
            self.lines.clear()
            self.made.clear()
            self.hold, self.playing, self.ramp = "playing", None, None
            self.started = None
        return unheard

    def idle(self):
        with self.audio_lock:
            pending = bool(self.audio) or bool(len(self.output))
        return self.busy <= 0 and not pending

    def wait(self, timeout=60.0):
        ends = time.monotonic() + timeout
        while not self.idle() and time.monotonic() < ends:
            time.sleep(0.05)

    def synthesise(self):
        while True:
            line, text = self.texts.get()
            self.cut.clear()
            began, made = time.monotonic(), 0
            self.began[line] = began
            try:
                for chunk in self.model.generate_audio_stream(self.state, text, stop=self.cut):
                    if self.cut.is_set():
                        break
                    samples = chunk.numpy().astype(np.float32)
                    made += len(samples)
                    self.play(samples, line)
            except Exception:
                log.exception("could not say %r", text)
            finally:
                took = time.monotonic() - began
                if made and took > 0 and not self.cut.is_set():
                    # HOW MANY SECONDS OF VOICE THIS COMPUTER MAKES PER SECOND, SMOOTHED OVER SENTENCES.
                    now = made / self.rate / took
                    self.pace = now if self.pace is None else 0.7 * self.pace + 0.3 * now
                    log.debug("voice made at %.2fx real time", self.pace)
                self.began.pop(line, None)
                if not self.cut.is_set():
                    # THE END OF A SENTENCE IS MARKED IN THE AUDIO, SO IT COUNTS AS HEARD ONLY ONCE IT HAS PLAYED.
                    self.play(None, line)
                with self.busy_lock:
                    self.busy -= 1

    def play(self, samples, line=None):
        with self.audio_lock:
            self.audio.append((line, samples))
            if line is not None and samples is not None:
                self.made.setdefault(line, []).append(samples)
        self.ensure_stream()

    def ensure_stream(self):
        if self.stream is not None:
            return
        self.follow_output()
        index = self.named_output()
        try:
            self.stream = sd.OutputStream(samplerate=self.rate, channels=1, dtype="float32",
                                          blocksize=int(self.rate * 0.03), callback=self.fill, device=index)
            self.stream.start()
            log.info("speaking through %s", sd.query_devices(index, "output")["name"])
        except Exception:
            log.exception("no speaker to play through")
            self.stream = None

    def named_output(self):
        """The speaker picked in settings, learning the devices again if it was plugged in since; None means the system's."""
        if not self.device:
            return None
        for attempt in range(2):
            for i, d in enumerate(sd.query_devices()):
                if d["max_output_channels"] > 0 and self.device.lower() in d["name"].lower():
                    return i
            if attempt == 0:
                self.refresh_devices()
        log.info("%s is not connected; speaking through the system's output", self.device)
        return None

    def follow_output(self):
        """The sound library learns the devices once; if the output changed since (headphones in or out), it learns them again."""
        if sys.platform != "darwin" or self.device:
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
            while written < frames and (self.audio or len(self.output)) and self.hold != "paused":
                if len(self.output):
                    take = min(frames - written, len(self.output))
                    out[written:written + take, 0] = self.output[:take]
                    self.output = self.output[take:]
                    written += take
                    continue
                line, head = self.audio[0]
                if head is None:
                    if self.stretcher is not None and (len(self.stretcher.input) or self.stretcher.tail is not None):
                        self.output = self.stretcher.flush()
                        continue
                    self.audio.popleft()
                    self.lines.pop(line, None)
                    self.made.pop(line, None)
                    self.reset_stretch()
                    continue
                speed = self.speed if line is not None else 1.0
                if speed != 1.0 and line != self.started and not self.ready(line, speed):
                    break
                if line is not None:
                    self.playing = line
                    self.started = line
                if speed == 1.0 and self.stretcher is not None and (len(self.stretcher.input) or self.stretcher.tail is not None):
                    self.output = self.stretcher.unstretched()
                    continue
                if speed != 1.0:
                    if self.stretcher is None:
                        self.stretcher = Stretcher(self.rate)
                    take = min(max(1, int(self.rate * 0.03)), len(head))
                    self.output = self.stretcher.process(head[:take], speed)
                    if take == len(head):
                        self.audio.popleft()
                    else:
                        self.audio[0] = (line, head[take:])
                    continue
                take = min(frames - written, len(head))
                out[written:written + take, 0] = head[:take]
                written += take
                if take == len(head):
                    self.audio.popleft()
                else:
                    self.audio[0] = (line, head[take:])
            # RAN OUT MID-SENTENCE: FADE THE LAST FEW MILLISECONDS AND FADE BACK IN, SO A GAP IS NOT A CLICK.
            dry = written < frames and self.hold == "playing" and self.playing in self.lines
            if dry and written:
                edge = min(written, int(self.rate * 0.005))
                out[written - edge:written, 0] *= np.linspace(1, 0, edge, dtype=np.float32)
            if dry:
                self.ramp = "in"
            # ONE BLOCK OF FADE EACH WAY, SO A PAUSE IS NOT A CLICK.
            if self.hold == "fading":
                out[:written, 0] *= np.linspace(1, 0, written, dtype=np.float32)
                self.hold, self.paused_at = "paused", time.monotonic()
            elif self.ramp == "in" and written:
                out[:written, 0] *= np.linspace(0, 1, written, dtype=np.float32)
                self.ramp = None
        out[written:, 0] = 0
        if written:
            self.last_sound = time.monotonic()
        self.on_level(float(np.sqrt(np.mean(out[:, 0] ** 2))) if written else 0.0)

    def ready(self, line, speed):
        """Whether a sentence can start at this speed and play to its end without waiting on the voice being made."""
        queued = 0
        for each, samples in self.audio:
            if each != line:
                break
            if samples is None:
                return True
            queued += len(samples)
        seconds = queued / self.rate
        # HOW FAST THIS SENTENCE IS BEING MADE RIGHT NOW, ONCE THERE IS A LITTLE TO GO ON; ELSE HOW FAST THE LAST ONES WERE.
        began = self.began.get(line)
        elapsed = time.monotonic() - began if began is not None else 0.0
        live = seconds / elapsed if elapsed > 0.2 else None
        known = [p for p in (live, self.pace) if p is not None]
        if not known:
            return False
        # THE SLOWER OF THE TWO, AND A LITTLE SLOWER STILL, SINCE A GAP SOUNDS WORSE THAN A SHORT WAIT.
        pace = 0.9 * min(known)
        # PLAYED AT speed WHILE MADE AT pace, A SENTENCE OF LENGTH L NEEDS L * (1 - pace / speed) SECONDS MADE AHEAD.
        ahead = LONGEST_SENTENCE * max(0.0, 1 - pace / speed)
        return seconds >= max(0.25, ahead)

    def reset_stretch(self):
        if self.stretcher is not None:
            self.stretcher.reset()
        self.output = np.empty(0, np.float32)

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