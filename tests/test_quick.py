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


def test_a_greeting_is_answered_without_a_model():
    assert match("Hi.")[0] == "reply"
    assert match("Thank you!")[0] == "reply"
    assert match("hi, can you open chrome") != ("reply", {"text": "Hi! What can I do for you?"})


def test_levels_are_said_as_a_direction_and_followed_up():
    from happy.agent import quick

    assert match("Can you lower the brightness of the screen?") == ("set_brightness", {"change": "down", "by": 10})
    quick.remember("set_brightness")
    assert match("Make it forty.") == ("set_brightness", {"level": 40})
    assert match("a bit more") == ("set_brightness", {"change": "up", "by": 5})


def test_coding_goes_to_a_coding_agent_with_its_project():
    assert match("fix the failing tests in the open slate project") == (
        "hand_off_coding", {"task": "fix the failing tests in the open slate project", "folder": "open slate"})
