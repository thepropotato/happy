"""Everyday requests that must never wait on a model."""

from happy.agent.quick import match


def test_media_always_goes_to_the_model():
    for said in ("play", "pause", "next song", "resume the video please", "play the video",
                 "play the telugu trailer of om movie", "play some lofi on youtube", "is the music playing"):
        assert match(said) is None, said


def test_asking_for_something_new_still_goes_to_the_model():
    assert match("what is this video about") is None


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


def test_handing_off_is_left_to_the_model():
    for said in ("fix the failing tests in the open slate project", "write a shopping list in the notes app",
                 "create a file called test.txt on the desktop"):
        assert match(said) is None


def test_the_machine_answers_battery_wifi_and_power_without_a_model():
    assert match("How much battery is left?") == ("battery", {})
    assert match("turn off the wifi") == ("wifi", {"action": "off"})
    assert match("is the wifi on") == ("wifi", {})
    assert match("restart my mac") == ("power", {"action": "restart"})
    assert match("cancel the shutdown") == ("power", {"action": "cancel"})
    assert match("is wifi connected") == ("connections", {"about": "wifi"})


def test_weather_now_is_quick_and_another_day_goes_to_the_model():
    assert match("what's the weather") == ("weather", {"where": ""})
    assert match("weather in new york") == ("weather", {"where": "new york"})
    assert match("how's the weather in springfeld illinois currently") == ("weather", {"where": "springfeld illinois"})
    assert match("what's the weather like in springfield tomorrow") is None
    assert match("will it rain this afternoon") is None


def test_listing_reminders_is_quick_and_setting_one_is_not():
    assert match("what reminders do I have") == ("reminder", {"action": "list"})
    assert match("remind me to call mom at four") is None


def test_days_until_a_date_are_counted_in_code():
    from datetime import date

    from happy.tools.status import days_until

    today = date(2026, 10, 25)
    assert days_until("christmas", today) == "Christmas is in 61 days, on Friday 25 December."
    assert days_until("new year", today) == "New Year is in 68 days, on Friday 1 January 2027."
    assert days_until("21 may", today) == "Friday 21 May 2027 is in 208 days."
    assert match("how many days are left until christmas") == ("clock", {"until": "christmas"})
    assert match("how long until my birthday") is None
