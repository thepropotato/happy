"""Feeds recorded speech through the listening pipeline, mic-free, and checks what comes out."""

import queue
import threading
import time
import wave
from pathlib import Path

import numpy as np
import pytest

from happy.ears import listen
from happy.ears.stt import Transcriber
from happy.ears.wake import addressed

CLIPS = Path(__file__).parent / "clips"


def load(name):
    with wave.open(str(CLIPS / name)) as clip:
        return np.frombuffer(clip.readframes(clip.getnframes()), np.int16).astype(np.float32) / 32768


def ears_hearing(audio, **kwargs):
    heard, states = [], []
    ears = listen.Ears("Happy", on_heard=lambda text, how: heard.append((text, how)), on_state=states.append, **kwargs)
    ears.stt = Transcriber()
    ears.segment = listen.Endpoint(wait=float("inf"))
    worker = threading.Thread(target=ears.run, daemon=True)
    worker.start()
    for start in range(0, len(audio), listen.BLOCK):
        ears.blocks.put(audio[start:start + listen.BLOCK])
    for _ in range(int(1.5 * listen.RATE / listen.BLOCK)):
        ears.blocks.put(np.zeros(listen.BLOCK, np.float32))
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
