"""Runs the voice against a fake sound card: sentences queue, play, report levels and can be cut off."""

import threading
import time

import numpy as np
import pytest

from happy.speech import speaker as voice


class FakeCard:
    """Pulls audio from the callback in real time, like a sound card would."""

    played = []

    def __init__(self, samplerate, channels, dtype, blocksize, callback, device=None):
        self.rate, self.block, self.callback = samplerate, blocksize, callback
        self.running = False

    def start(self):
        self.running = True
        threading.Thread(target=self.pump, daemon=True).start()

    def pump(self):
        out = np.zeros((self.block, 1), np.float32)
        while self.running:
            self.callback(out, self.block, None, None)
            FakeCard.played.append(float(np.abs(out).max()))
            time.sleep(self.block / self.rate)

    def stop(self):
        self.running = False

    def close(self):
        pass


@pytest.fixture(scope="module")
def spoken():
    voice.sd.OutputStream = FakeCard
    levels, talking = [], []
    speaker = voice.Speaker("alba", on_level=levels.append, on_speaking=talking.append)
    speaker.start()
    return speaker, levels, talking


def test_speaks_then_goes_quiet(spoken):
    speaker, levels, talking = spoken
    FakeCard.played.clear()
    started = time.monotonic()
    speaker.say("Brightness at twenty.")
    while max(FakeCard.played or [0]) < 0.01 and time.monotonic() - started < 5:
        time.sleep(0.01)
    first_sound = time.monotonic() - started
    speaker.wait(10)
    time.sleep(0.4)
    assert first_sound < 1.0, first_sound
    assert max(levels) > 0.01
    assert talking[:1] == [True] and talking[-1] is False


def test_stop_cuts_it_off(spoken):
    speaker, _, _ = spoken
    speaker.say("This is a long sentence that should never be heard to the end because someone talks over it.")
    speaker.say("And this one should never start.")
    time.sleep(0.5)
    speaker.stop()
    time.sleep(0.3)
    assert speaker.idle()


def test_nothing_unspeakable_is_queued(spoken):
    speaker, _, _ = spoken
    assert speaker.say("https://example.com/a/b") == "a link to Example"
    speaker.stop()
    assert speaker.say("**") == ""


def test_the_wake_chime_is_not_happy_talking(spoken):
    speaker, _, talking = spoken
    speaker.stop()
    time.sleep(0.4)
    talking.clear()
    speaker.blip()
    time.sleep(0.8)
    assert True not in talking, talking
