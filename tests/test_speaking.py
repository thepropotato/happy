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


def test_stop_cuts_it_off_and_hands_back_what_was_not_heard(spoken):
    speaker, _, _ = spoken
    speaker.say("This is a long sentence that should never be heard to the end because someone talks over it.")
    speaker.say("And this one should never start.")
    time.sleep(0.5)
    unheard = speaker.stop()
    time.sleep(0.3)
    assert speaker.idle()
    assert unheard == ["This is a long sentence that should never be heard to the end because someone talks over it.",
                       "And this one should never start."]


def wait_for_sound(speaker, seconds=5):
    ends = time.monotonic() + seconds
    while max(FakeCard.played[-3:] or [0]) < 0.01 and time.monotonic() < ends:
        time.sleep(0.01)


def test_a_pause_keeps_the_place_and_resumes(spoken):
    speaker, _, _ = spoken
    speaker.stop()
    FakeCard.played.clear()
    speaker.say("One sentence that is long enough to pause somewhere in the middle of it, comfortably.")
    wait_for_sound(speaker)
    speaker.pause()
    time.sleep(0.3)
    FakeCard.played.clear()
    time.sleep(0.4)
    assert speaker.paused() and max(FakeCard.played) == 0.0 and not speaker.idle()
    speaker.resume()
    wait_for_sound(speaker)
    assert not speaker.paused() and max(FakeCard.played[-3:]) > 0.01
    speaker.wait(20)
    assert speaker.idle() and speaker.stop() == []


def test_a_long_pause_goes_back_to_the_start_of_the_sentence(spoken, monkeypatch):
    speaker, _, _ = spoken
    speaker.stop()
    monkeypatch.setattr(voice, "REWIND_AFTER", 0.2)
    speaker.say("A sentence that will be said again from its very first word after the pause.")
    wait_for_sound(speaker)
    time.sleep(0.6)
    speaker.pause()
    time.sleep(0.4)
    with speaker.audio_lock:
        left = sum(len(chunk) for line, chunk in speaker.audio if chunk is not None)
        whole = sum(len(chunk) for chunk in speaker.made[speaker.playing])
    speaker.resume()
    with speaker.audio_lock:
        again = sum(len(chunk) for line, chunk in speaker.audio if chunk is not None)
    assert left < whole and again >= whole, (left, whole, again)
    speaker.stop()


def test_a_finished_sentence_is_not_handed_back(spoken):
    speaker, _, _ = spoken
    speaker.stop()
    speaker.say("Short one.")
    speaker.wait(10)
    speaker.say("A second sentence, long enough to still be playing when it is stopped right now.")
    wait_for_sound(speaker)
    assert speaker.stop() == ["A second sentence, long enough to still be playing when it is stopped right now."]


def test_nothing_unspeakable_is_queued(spoken):
    speaker, _, _ = spoken
    assert speaker.say("https://example.com/a/b") == "a link to Example"
    speaker.stop()
    assert speaker.say("**") == ""


def test_a_wake_up_before_the_voice_has_loaded_is_silent():
    speaker = voice.Speaker("alba")
    speaker.blip()
    assert not speaker.audio


def test_the_wake_chime_is_not_happy_talking(spoken):
    speaker, _, talking = spoken
    speaker.stop()
    time.sleep(0.4)
    talking.clear()
    speaker.blip()
    time.sleep(0.8)
    assert True not in talking, talking


def test_quote_marks_and_stretched_letters_are_not_handed_to_the_voice():
    from happy.speech.spoken_text import speakable

    assert speakable("It says, “Okiee okie.”") == "It says, Okiee okie."
    assert speakable('She said "Bruuu, sooo good"') == "She said Bru, so good"
    assert speakable("World War III, don't") == "World War III, don't"
