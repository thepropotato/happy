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
    assert "brightness" in heard[0][0].lower() and not heard[0][0].lower().startswith("hey")


@pytest.mark.skipif(not CLIPS.exists(), reason="no recorded clips")
def test_name_in_passing_is_ignored():
    heard, states = ears_hearing(load("neg1.wav"))
    assert heard == [] and "listening" not in states


def test_addressed():
    assert addressed("Hey Happy, set the brightness to 20%.", "Happy") == "set the brightness to 20%."
    assert addressed("Happy. Pause the video.", "Happy") == "Pause the video."
    assert addressed("I was so happy yesterday.", "Happy") is None
    assert addressed("Okay, Happy, what's on my screen?", "Happy") == "what's on my screen?"
    assert addressed("Hey Happy.", "Happy") == ""


@pytest.mark.skipif(not CLIPS.exists(), reason="no recorded clips")
def test_name_with_a_pause_after_it_still_wakes():
    heard, _ = ears_hearing(load("wake2.wav"))
    assert heard and "pause" in heard[0][0].lower(), heard


def test_a_name_heard_slightly_wrong_still_counts():
    assert addressed("Hey Damon, pause the video.", "Daemon") == "pause the video."
    assert addressed("Demon, what is on my screen?", "Daemon") == "what is on my screen?"
    assert addressed("Happi, mute.", "Happy") == "mute."
    assert addressed("Hippie, mute.", "Happy") is None
    assert addressed("Hey Jarvis, lock the screen.", "Happy") is None


def test_a_sentence_that_only_starts_with_the_word_is_not_a_request():
    assert addressed("Happy birthday to you!", "Happy") is None
    assert addressed("Happy new year, everyone.", "Happy") is None
    assert addressed("Happy open chrome", "Happy") == "open chrome"
    assert addressed("Happy", "Happy") == ""


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
