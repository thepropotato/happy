"""Speaking speed without a microphone, model or sound card."""

import time
import types

import numpy as np
import pytest

from happy.agent import quick
from happy.config import Config, SPEECH_SPEEDS, speech_speed
from happy.speech.speaker import Speaker
from happy.speech.stretch import Stretcher

RATE = 24000


def sine(seconds=2):
    return np.sin(2 * np.pi * 220 * np.arange(round(RATE * seconds)) / RATE).astype(np.float32)


def stretch(sound, speed, chunk):
    stretcher = Stretcher(RATE)
    parts = [stretcher.process(sound[at:at + chunk], speed) for at in range(0, len(sound), chunk)]
    return np.concatenate([*parts, stretcher.flush()])


@pytest.mark.parametrize("speed", [0.75, 1.25, 1.5, 1.75])
def test_duration_changes_without_changing_pitch(speed):
    result = stretch(sine(), speed, RATE * 2)
    assert len(result) / RATE == pytest.approx(2 / speed, rel=0.05)
    spectrum = np.abs(np.fft.rfft(result * np.hanning(len(result))))
    dominant = np.fft.rfftfreq(len(result), 1 / RATE)[np.argmax(spectrum)]
    assert dominant == pytest.approx(220, abs=3)


def test_normal_speed_is_exactly_the_input():
    sound = sine()
    stretcher = Stretcher(RATE)
    assert stretcher.process(sound, 1.0) is sound
    assert not len(stretcher.flush())


@pytest.mark.parametrize("speed", [0.75, 1.5, 1.75])
def test_small_chunks_match_one_big_chunk(speed):
    sound = sine()
    whole = stretch(sound, speed, len(sound))
    pieces = stretch(sound, speed, 137)
    assert len(pieces) == len(whole)
    np.testing.assert_array_equal(pieces, whole)


@pytest.mark.parametrize("length", [1, 200, 599, 600, 900])
def test_sentence_tail_is_not_lost(length):
    result = stretch(sine()[:length], 0.75, 137)
    assert len(result) == round(length / 0.75)
    assert np.isfinite(result).all()


@pytest.mark.parametrize(("said", "args"), [
    ("talk faster", {"change": "up"}),
    ("speak faster", {"change": "up"}),
    ("slow down", {"change": "down"}),
    ("talk slower", {"change": "down"}),
    ("speak slower", {"change": "down"}),
    ("normal speed", {"speed": 1.0}),
    ("talk at normal speed", {"speed": 1.0}),
    ("set the speed to 1.5", {"speed": 1.5}),
    ("speed 1.25x", {"speed": 1.25}),
    ("speed 3x", {"speed": 1.75}),
    ("Please speak faster!", {"change": "up"}),
])
def test_speed_commands_are_quick(said, args):
    assert quick.match(said) == ("set_speech_speed", args)


def test_unrelated_words_are_not_speed_commands():
    for said in ("I'm happy today", "speed of light", "talk faster about the weather"):
        assert quick.match(said) is None


def test_config_snaps_and_persists_a_float(tmp_path):
    cfg = Config(tmp_path / "config.toml")
    assert cfg.get("speech_speed") == 1.0
    cfg.set("speech_speed", 1.43)
    cfg.save()
    assert Config(cfg.path).get("speech_speed") == 1.5
    assert "speech_speed = 1.5" in cfg.path.read_text()
    cfg.path.write_text("speech_speed = 3.0\n")
    assert Config(cfg.path).get("speech_speed") == 1.75


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, "quick"])
def test_invalid_speed_is_rejected(value):
    with pytest.raises(ValueError):
        speech_speed(value)


def speaker(speed=1.0):
    one = Speaker(speed=speed)
    one.rate = RATE
    one.ensure_stream = lambda: None
    return one


def pull(one, frames=720):
    out = np.empty((frames, 1), np.float32)
    one.fill(out, frames, None, None)
    return out[:, 0]


def queued(one, sound, line=0):
    one.lines[line] = f"Sentence {line}."
    one.play(sound, line)
    one.play(None, line)


def drain(one):
    parts = []
    for _ in range(1000):
        if one.idle():
            return np.concatenate(parts) if parts else np.empty(0, np.float32)
        parts.append(pull(one))
    pytest.fail("Speaker did not finish")


def test_default_callback_is_an_exact_passthrough():
    one = speaker()
    sound = sine()
    queued(one, sound)
    np.testing.assert_array_equal(drain(one)[:len(sound)], sound)
    assert one.stretcher is None
    assert not one.lines and not one.made


def test_speed_changes_audio_already_queued():
    one = speaker()
    sound = sine()
    queued(one, sound)
    np.testing.assert_array_equal(pull(one), sound[:720])
    one.speed = 1.5
    remainder = drain(one)
    assert len(remainder) / RATE == pytest.approx((2 - 0.03) / 1.5, abs=0.06)
    assert one.idle() and not one.made


def test_returning_to_normal_speed_keeps_playing():
    one = speaker(0.75)
    queued(one, sine())
    pull(one)
    one.speed = 1.0
    assert np.max(np.abs(drain(one))) > 0.9
    assert not len(one.stretcher.input)

def test_returning_to_normal_speed_does_not_click():
    sound = sine()
    stretcher = Stretcher(RATE)
    first = stretcher.process(sound[:4000], 0.75)
    transition = stretcher.unstretched()
    result = np.concatenate((first, transition, sound[4000:]))
    assert np.max(np.abs(np.diff(result))) < 0.1


def test_pause_rewind_stop_and_sentence_boundaries():
    one = speaker(1.5)
    sound = sine(0.5)
    queued(one, sound)
    queued(one, sound, 1)
    pull(one)
    assert one.made[0][0] is sound
    one.pause()
    pull(one)
    assert one.paused()
    assert not np.any(pull(one))
    one.paused_at = time.monotonic() - 3
    one.resume()
    assert not len(one.output) and not len(one.stretcher.input)
    assert one.audio[0][1] is sound
    drain(one)
    assert one.stop() == []
    queued(one, sound, 2)
    pull(one)
    assert one.stop() == ["Sentence 2."]
    assert one.idle() and not len(one.stretcher.input)


def test_chime_is_not_stretched():
    one = speaker(1.75)
    sound = sine(0.07)
    one.play(sound)
    np.testing.assert_array_equal(drain(one)[:len(sound)], sound)
    assert one.stretcher is None


def test_tool_saves_steps_and_updates_running_speaker(tmp_path, monkeypatch):
    from happy.app import Happy
    from happy.tools import controls

    path = tmp_path / "config.toml"
    monkeypatch.setattr(controls, "Config", lambda: Config(path))
    values = []
    happy = Happy(Config(path), types.SimpleNamespace(speed=values.append))
    happy.speaker = speaker()
    monkeypatch.setattr(controls, "on_speed", happy.speed_changed)
    assert controls.set_speech_speed(change="up") == "Speaking at 1.25x."
    assert happy.speaker.speed == Config(path).get("speech_speed") == 1.25
    controls.set_speech_speed(change="down")
    assert happy.speaker.speed == 1.0
    controls.set_speech_speed(speed=3)
    controls.set_speech_speed(change="up")
    assert happy.speaker.speed == SPEECH_SPEEDS[-1]
    controls.set_speech_speed(speed=0)
    controls.set_speech_speed(change="down")
    assert happy.speaker.speed == SPEECH_SPEEDS[0]
    assert values == [1.25, 1.0, 1.75, 1.75, 0.75, 0.75]


def test_mid_reply_commands_do_not_cancel_the_answer(tmp_path, monkeypatch):
    from happy.app import Happy
    from happy.tools import controls

    path = tmp_path / "config.toml"
    monkeypatch.setattr(controls, "Config", lambda: Config(path))
    notices, said, states = [], [], []
    face = types.SimpleNamespace(speed=lambda value: None, note=notices.append, state=states.append)
    happy = Happy(Config(path), face)
    happy.speaker = speaker()
    happy.speaker.speaking = True
    queued(happy.speaker, sine())
    happy.say = said.append
    monkeypatch.setattr(controls, "on_speed", happy.speed_changed)
    happy.begin("talk faster", "typed")
    assert happy.speaker.speed == 1.25
    assert happy.task is None and happy.speaker.lines
    happy.speaker.pause()
    pull(happy.speaker)
    happy.cut_in("Happy, slow down.", by_name=True)
    assert happy.speaker.speed == 1.0 and not happy.speaker.paused()
    assert happy.task is None and happy.speaker.lines
    assert notices == said == ["Speaking at 1.25x.", "Speaking at 1x."]
    assert states == ["speaking", "speaking"]


def test_settings_uses_the_same_saved_value(tmp_path, monkeypatch):
    from happy.ui import settings

    path = tmp_path / "config.toml"
    monkeypatch.setattr(settings, "Config", lambda: Config(path))
    changed = []
    panel = settings.Settings(lambda word: None, changed=changed.append)
    panel.send = lambda **extra: None
    panel.order({"do": "set", "key": "speech_speed", "value": 1.44})
    assert Config(path).get("speech_speed") == 1.5
    assert changed == ["speech_speed"]
    panel.order({"do": "set", "key": "speech_speed", "value": "fast"})
    assert panel.notice and Config(path).get("speech_speed") == 1.5
