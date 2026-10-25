"""Reminders and routines kept, fired, moved and replayed, in a throwaway database."""

from datetime import datetime, timedelta

import pytest

from happy import history, reminders, routines


@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "FILE", tmp_path / "history.db")


def tool(**args):
    from happy.tools.reminders import reminder

    return reminder(**args)


def test_set_says_the_time_back_in_full_and_lists_it():
    said = tool(action="set", what="call the dentist", when="in two hours")
    assert said.startswith("Reminder set: call the dentist, ")
    assert "today" in said or "tomorrow" in said
    assert "call the dentist" in tool(action="list")


def test_an_unclear_time_sets_nothing():
    assert tool(action="set", what="water the plants", when="sometime").startswith("Not set:")
    assert tool(action="list") == "No reminders are set."


def test_a_one_off_fires_once_and_a_repeating_one_rolls_on():
    now = datetime.now()
    reminders.add("tablets", now - timedelta(seconds=5))
    reminders.add("drink water", now - timedelta(seconds=5), {"every": 3600})
    fired = reminders.due(now)
    assert [r["what"] for r in fired] == ["tablets", "drink water"]
    assert not any(r["missed"] for r in fired)
    assert [r["what"] for r in reminders.upcoming()] == ["drink water"]
    assert reminders.upcoming()[0]["at"] > now
    assert reminders.due(now) == []


def test_one_missed_while_off_is_marked_missed():
    now = datetime.now()
    reminders.add("parking", now - timedelta(hours=3))
    assert reminders.due(now)[0]["missed"]


def test_change_moves_it_and_forget_drops_it():
    tool(action="set", what="call the dentist", when="tomorrow at 4")
    assert "5 PM" in tool(action="change", what="dentist", when="tomorrow at 5 pm")
    assert tool(action="forget", what="dentist") == "Forgot the reminder to call the dentist."
    assert tool(action="list") == "No reminders are set."


def test_changing_the_hour_of_a_daily_one_keeps_it_daily():
    tool(action="set", what="stretch", when="every day at 8")
    said = tool(action="change", what="stretch", when="at 6 pm")
    assert "every day at 6 PM" in said


def test_snooze_brings_back_the_one_that_just_went_off():
    now = datetime.now()
    reminders.add("tea", now - timedelta(seconds=1))
    reminders.due(now)
    assert tool(action="snooze").startswith("I'll remind you again")
    assert [r["what"] for r in reminders.upcoming()] == ["tea"]


def test_two_that_match_are_asked_about_not_guessed():
    tool(action="set", what="call mom", when="at 9 pm")
    tool(action="set", what="call dad", when="at 10 pm")
    assert tool(action="forget", what="call").startswith("More than one matches")


def test_a_routine_is_saved_run_by_name_and_set_on_a_timer():
    from happy.tools.routines import routine

    said = routine(action="save", name="Morning brief", steps=["what's the weather", "any unread WhatsApp messages"])
    assert "morning brief" in said
    assert routines.asked_for("run my morning brief")["name"] == "morning brief"
    assert routines.asked_for("Morning brief.")["name"] == "morning brief"
    assert routines.asked_for("what's the weather") is None
    assert "1. what's the weather\n2. any unread WhatsApp messages" in routines.request(routines.named("morning brief"))
    assert tool(action="set", when="every weekday at 7", routine="morning brief").startswith("Reminder set: run morning brief")
    assert tool(action="set", when="at 7", routine="evening thing") == "There is no saved routine called evening thing."
    assert routine(action="rename", name="morning brief", new_name="daily brief").startswith("Renamed")
    assert routine(action="forget", name="daily brief") == "Forgot the daily brief routine."
    assert routine(action="list") == "No routines are saved."


def test_saving_with_no_steps_keeps_the_request_before_it():
    from happy.tools.routines import routine

    history.begin("how's the weather in london", "spoken")
    history.begin("save that as a routine called london", "spoken")
    assert routine(action="save", name="london").startswith("Saved the london routine: how's the weather in london")
