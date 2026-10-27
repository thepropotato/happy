"""Feeds recorded speech through the listening pipeline, mic-free, and checks what comes out."""

import queue
import threading
import time
import wave
from pathlib import Path

import numpy as np
import pytest

from happy.speech import listener
from happy.speech.transcriber import Transcriber
from happy.speech.addressing import addressed

CLIPS = Path(__file__).parent / "clips"


def load(name):
    with wave.open(str(CLIPS / name)) as clip:
        return np.frombuffer(clip.readframes(clip.getnframes()), np.int16).astype(np.float32) / 32768


def ears_hearing(audio, **kwargs):
    heard, states = [], []
    ears = listener.Listener("Happy", on_heard=lambda text, how: heard.append((text, how)), on_state=states.append, **kwargs)
    ears.stt = Transcriber()
    ears.fresh_segment()
    worker = threading.Thread(target=ears.run, daemon=True)
    worker.start()
    for start in range(0, len(audio), listener.BLOCK):
        ears.blocks.put(audio[start:start + listener.BLOCK])
    for _ in range(int(1.5 * listener.RATE / listener.BLOCK)):
        ears.blocks.put(np.zeros(listener.BLOCK, np.float32))
    deadline = time.time() + 20
    while ears.blocks.qsize() and time.time() < deadline:
        time.sleep(0.05)
    time.sleep(1.0)
    ears.stopping.set()
    return heard, states


@pytest.mark.skipif(not CLIPS.exists(), reason="no recorded clips")
def test_name_then_request_is_heard_as_one_request():
    heard, _ = ears_hearing(load("wake.wav"))
    assert heard and heard[0][1] == "wake", heard
    assert "brightness" in heard[0][0].lower() and "happy" not in heard[0][0].lower()


@pytest.mark.skipif(not CLIPS.exists(), reason="no recorded clips")
def test_name_in_passing_is_ignored():
    heard, states = ears_hearing(load("neg1.wav"))
    assert heard == [] and "listening" not in states


def test_addressed():
    assert addressed("Hey Happy, set the brightness to 20%.", "Happy") == "Hey, set the brightness to 20%."
    assert addressed("Happy. Pause the video.", "Happy") == "Pause the video."
    assert addressed("I was so happy yesterday.", "Happy") is None
    assert addressed("Okay, Happy, what's on my screen?", "Happy") == "Okay, what's on my screen?"
    assert addressed("Happy.", "Happy") == ""


def test_a_greeting_with_the_name_is_answered_whole():
    assert addressed("Hey Happy.", "Happy") == "Hey Happy."
    assert addressed("Hi Happy", "Happy") == "Hi Happy"
    assert addressed("Hello, Happy.", "Happy") == "Hello, Happy."
    assert addressed("Hi Happy, open YouTube.", "Happy") == "Hi, open YouTube."
    assert addressed("Happy, hi.", "Happy") == "hi."


@pytest.mark.skipif(not CLIPS.exists(), reason="no recorded clips")
def test_name_with_a_pause_after_it_still_wakes():
    heard, _ = ears_hearing(load("wake2.wav"))
    assert heard and "pause" in heard[0][0].lower(), heard


def test_a_name_heard_slightly_wrong_still_counts():
    assert addressed("Hey Damon, pause the video.", "Daemon") == "Hey, pause the video."
    assert addressed("Demon, what is on my screen?", "Daemon") == "what is on my screen?"
    assert addressed("Happi, mute.", "Happy") == "mute."
    assert addressed("Hippie, mute.", "Happy") is None
    assert addressed("Hey Jarvis, lock the screen.", "Happy") is None


def test_a_sentence_that_only_starts_with_the_word_is_not_a_request():
    assert addressed("Happy birthday to you!", "Happy") is None
    assert addressed("Happy new year, everyone.", "Happy") is None
    assert addressed("Happy open chrome", "Happy") == "open chrome"
    assert addressed("Happy", "Happy") == ""


def test_a_greeting_after_the_name_is_a_request():
    assert addressed("Daemon hello", "Daemon") == "hello"
    assert addressed("Daemon, hello.", "Daemon") == "hello."


@pytest.mark.skipif(not CLIPS.exists(), reason="no recorded clips")
def test_the_name_is_acknowledged_while_the_sentence_is_still_going():
    """The chime comes when the name is heard, before the request has finished."""
    audio = load("wake.wav")
    heard, states = [], []
    ears = listener.Listener("Happy", on_heard=lambda text, how: heard.append(text), on_state=states.append)
    ears.stt = Transcriber()
    ears.fresh_segment()
    fed = 0.0
    woke_at = None
    for start in range(0, len(audio), listener.BLOCK):
        ears.overhear(audio[start:start + listener.BLOCK], ears.mode)
        fed += listener.BLOCK / listener.RATE
        if woke_at is None and "listening" in states:
            woke_at = fed
    speech_ends = len(np.trim_zeros(audio, "b")) / listener.RATE
    assert woke_at is not None and woke_at < speech_ends - 1.0, (woke_at, speech_ends)


def talking_over(audio, echo=lambda text: False, headphones=False):
    """Feeds audio to a listener that believes Happy is speaking: on headphones, or with echo cancellation on."""
    paused, said = [], []
    ears = listener.Listener("Happy", on_barge=lambda: paused.append(True),
                             on_cut_in=lambda text, by_name: said.append(listener.meaning(text, "Happy", by_name)), echo=echo)
    ears.stt = Transcriber()
    ears.mic = None if headphones else object()
    listener.on_headphones, real = (lambda: headphones), listener.on_headphones
    try:
        ears.deaf.set()
        ears.fresh_segment()
        silence = np.zeros(listener.BLOCK * 15, np.float32)
        for chunk in (audio, silence):
            for start in range(0, len(chunk), listener.BLOCK):
                ears.overhear(chunk[start:start + listener.BLOCK], ears.mode)
    finally:
        listener.on_headphones = real
    return paused, said


@pytest.mark.skipif(not CLIPS.exists(), reason="no recorded clips")
def test_talking_over_happy_by_name_pauses_him_and_is_a_request():
    paused, said = talking_over(load("wake2.wav"))
    assert paused and said and said[0][0] == "request" and "pause" in said[0][1].lower(), (paused, said)


@pytest.mark.skipif(not CLIPS.exists(), reason="no recorded clips")
def test_on_headphones_talking_over_happy_needs_no_name():
    paused, said = talking_over(load("neg1.wav"), headphones=True)
    assert paused and said and said[0][0] == "request", (paused, said)


@pytest.mark.skipif(not CLIPS.exists(), reason="no recorded clips")
def test_through_echo_cancellation_words_without_his_name_only_pause_him():
    # LEAKED ECHO TRANSCRIBES AS STRAY WORDS LIKE "I THINK", SO WORDS WITHOUT THE NAME MUST NOT START A TURN.
    paused, said = talking_over(load("neg1.wav"))
    assert said and said[0][0] == "carry on", (paused, said)


def test_noise_does_not_pause_happy():
    hiss = (np.random.default_rng(1).standard_normal(listener.RATE * 3) * 0.02).astype(np.float32)
    paused, said = talking_over(hiss)
    assert not paused and not said


@pytest.mark.skipif(not CLIPS.exists(), reason="no recorded clips")
def test_his_own_words_coming_back_only_pause_him():
    paused, said = talking_over(load("wake2.wav"), echo=lambda text: True)
    assert said and said[0][0] == "carry on", (paused, said)


def test_what_words_said_over_happy_ask_of_him():
    assert listener.meaning("Yeah.", "Happy") == ("carry on", "")
    assert listener.meaning("Okay, okay.", "Happy") == ("carry on", "")
    assert listener.meaning("Mm-hmm, right.", "Happy") == ("carry on", "")
    assert listener.meaning("Go on.", "Happy") == ("carry on", "")
    assert listener.meaning("", "Happy") == ("carry on", "")
    assert listener.meaning("Stop.", "Happy") == ("stop", "")
    assert listener.meaning("Okay, stop.", "Happy") == ("stop", "")
    assert listener.meaning("Happy, stop.", "Happy") == ("stop", "")
    assert listener.meaning("Thank you.", "Happy") == ("stop", "")
    assert listener.meaning("Wait.", "Happy") == ("wait", "")
    assert listener.meaning("Hold on.", "Happy") == ("wait", "")
    assert listener.meaning("Happy.", "Happy") == ("wait", "")
    assert listener.meaning("What does crore mean?", "Happy") == ("request", "What does crore mean?")
    assert listener.meaning("Happy, what does crore mean?", "Happy") == ("request", "what does crore mean?")
    assert listener.meaning("Hi.", "Happy") == ("request", "Hi.")
    assert listener.meaning("The.", "Happy") == ("request", "The.")
    assert listener.meaning("Hey Happy.", "Happy") == ("request", "Hey Happy.")
    assert listener.meaning("What does crore mean?", "Happy", by_name=True) == ("carry on", "")
    assert listener.meaning("Happy, what does crore mean?", "Happy", by_name=True) == ("request", "what does crore mean?")


def test_a_short_word_after_the_name_is_answered():
    heard, states = [], []
    ears = listener.Listener("Happy", on_heard=lambda text, how: heard.append((text, how)), on_state=states.append)
    for word in ("Hi,", "Ok.", "No.", "The."):
        ears.stt = lambda audio, word=word: word
        ears.finish(np.zeros(10, np.float32), "follow")
    assert heard == [("Hi,", "follow"), ("Ok.", "follow"), ("No.", "follow"), ("The.", "follow")] and "missed" not in states


def test_once_the_chime_has_played_the_sentence_is_a_request():
    heard = []
    ears = listener.Listener("Sam", on_heard=lambda text, how: heard.append((text, how)), on_state=lambda state: None)
    for said in ("Sam sing a rhyme.", "Sam the weather today", "Some, what time is it?"):
        ears.stt = lambda audio, said=said: said
        ears.finish(np.zeros(10, np.float32), "woken")
    assert heard == [("sing a rhyme.", "wake"), ("the weather today", "wake"), ("Some, what time is it?", "wake")]


def test_the_name_in_passing_without_the_chime_is_still_ignored():
    heard = []
    ears = listener.Listener("Sam", on_heard=lambda text, how: heard.append((text, how)), on_state=lambda state: None)
    ears.stt = lambda audio: "Sam said he would come over later."
    ears.finish(np.zeros(10, np.float32), "overheard")
    assert heard == []


def test_a_microphone_that_stops_handing_over_sound_is_reopened(monkeypatch):
    monkeypatch.setattr(listener, "STALLED", 0.3)
    reopened = []
    ears = listener.Listener("Happy", refresh_devices=lambda: reopened.append(time.monotonic()))
    ears.fresh_segment()
    threading.Thread(target=ears.run, daemon=True).start()
    time.sleep(1.0)
    ears.stopping.set()
    assert reopened


def test_a_stalled_echo_cancelled_mic_is_reopened_plain(monkeypatch):
    monkeypatch.setattr(listener, "STALLED", 0.3)
    ears = listener.Listener("Happy", refresh_devices=lambda: None)
    ears.mic, ears.opened_on = type("Stuck", (), {"engine": None})(), "John Doe’s AirPods Pro"
    ears.fresh_segment()
    threading.Thread(target=ears.run, daemon=True).start()
    time.sleep(1.0)
    ears.stopping.set()
    assert ears.plain_on == "John Doe’s AirPods Pro"
