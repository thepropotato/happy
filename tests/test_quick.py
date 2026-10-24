"""Everyday requests that must never wait on a model."""

from happy.agent.quick import match


def test_playing_what_is_on_screen_said_loosely():
    assert match("Can you play this video, continue this?") == ("media", {"action": "play"})
    assert match("resume the video please") == ("media", {"action": "play"})
    assert match("pause this video for a sec") == ("media", {"action": "pause"})
    assert match("can you stop the music") == ("media", {"action": "pause"})


def test_asking_for_something_new_still_goes_to_the_model():
    assert match("play some lofi on youtube") is None
    assert match("what is this video about") is None
    assert match("is the music playing") is None
