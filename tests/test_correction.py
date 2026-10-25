import types

from happy.app import Happy


def fresh():
    return types.SimpleNamespace(last_spoken=("", 0.0), correcting=Happy.correcting)


def say(happy, text, how="woken"):
    return Happy.corrected(happy, text, how)


def test_a_cue_soon_after_corrects_the_last_request():
    happy = fresh()
    say(happy, "what's the last message from jon")
    text, how = say(happy, "no, john doe")
    assert how == "correction" and "what's the last message from jon" in text and text.startswith("no, john doe")


def test_a_near_repeat_corrects_a_misheard_name():
    happy = fresh()
    say(happy, "what's the last message from jaine")
    text, how = say(happy, "what's the last message from jane")
    assert how == "correction"


def test_an_unrelated_request_is_its_own():
    happy = fresh()
    say(happy, "what's the last message from jane")
    assert say(happy, "what time is it") == ("what time is it", "woken")


def test_a_repeated_command_is_meant_twice():
    happy = fresh()
    say(happy, "volume up")
    assert say(happy, "volume up") == ("volume up", "woken")


def test_too_late_is_a_new_request():
    happy = fresh()
    say(happy, "what's the last message from jon")
    happy.last_spoken = (happy.last_spoken[0], happy.last_spoken[1] - 9)
    assert say(happy, "no, john doe")[1] == "woken"


def test_typing_is_never_merged():
    happy = fresh()
    say(happy, "what's the last message from jon")
    assert say(happy, "no, john doe", "typed") == ("no, john doe", "typed")
