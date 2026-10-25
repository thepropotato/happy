"""Spoken times against a fixed Wednesday lunchtime: the soonest future moment the words could mean."""

from datetime import datetime

import pytest

from happy.timing import Unclear, following, spoken, spoken_rule, when

NOW = datetime(2026, 10, 21, 13, 0)  # A WEDNESDAY, 1 PM.

ONE_OFF = [
    ("in ten minutes", datetime(2026, 10, 21, 13, 10)),
    ("in 2 hours", datetime(2026, 10, 21, 15, 0)),
    ("in an hour", datetime(2026, 10, 21, 14, 0)),
    ("in half an hour", datetime(2026, 10, 21, 13, 30)),
    ("in an hour and a half", datetime(2026, 10, 21, 14, 30)),
    ("20 minutes from now", datetime(2026, 10, 21, 13, 20)),
    ("at four", datetime(2026, 10, 21, 16, 0)),
    ("at 4", datetime(2026, 10, 21, 16, 0)),
    ("at 11", datetime(2026, 10, 21, 23, 0)),
    ("at 12:30", datetime(2026, 10, 22, 0, 30)),
    ("at 4:30 pm", datetime(2026, 10, 21, 16, 30)),
    ("at 9 am", datetime(2026, 10, 22, 9, 0)),
    ("at 16:45", datetime(2026, 10, 21, 16, 45)),
    ("at noon", datetime(2026, 10, 22, 12, 0)),
    ("at midnight", datetime(2026, 10, 22, 0, 0)),
    ("at half past four", datetime(2026, 10, 21, 16, 30)),
    ("at quarter to five", datetime(2026, 10, 21, 16, 45)),
    ("tomorrow", datetime(2026, 10, 22, 9, 0)),
    ("tomorrow at 4", datetime(2026, 10, 22, 16, 0)),
    ("tomorrow at 8", datetime(2026, 10, 22, 8, 0)),
    ("tomorrow morning", datetime(2026, 10, 22, 9, 0)),
    ("tomorrow evening at 7", datetime(2026, 10, 22, 19, 0)),
    ("tonight", datetime(2026, 10, 21, 20, 0)),
    ("tonight at 9", datetime(2026, 10, 21, 21, 0)),
    ("this evening", datetime(2026, 10, 21, 18, 0)),
    ("in the morning", datetime(2026, 10, 22, 9, 0)),
    ("on friday", datetime(2026, 10, 23, 9, 0)),
    ("friday at 5", datetime(2026, 10, 23, 17, 0)),
    ("next friday at 10 am", datetime(2026, 10, 23, 10, 0)),
    ("on wednesday at 3", datetime(2026, 10, 28, 15, 0)),
    ("on may 21", datetime(2027, 5, 21, 9, 0)),
    ("on the 21st of november at 6 pm", datetime(2026, 11, 21, 18, 0)),
    ("on the 25th", datetime(2026, 10, 25, 9, 0)),
    ("day after tomorrow at 10", datetime(2026, 10, 23, 10, 0)),
    ("2026-10-30T15:00", datetime(2026, 10, 30, 15, 0)),
]


@pytest.mark.parametrize("words,expected", ONE_OFF)
def test_a_one_off_is_the_soonest_moment_the_words_mean(words, expected):
    assert when(words, NOW) == (expected, None)


REPEATING = [
    ("every hour", datetime(2026, 10, 21, 14, 0), "every hour"),
    ("every 30 minutes", datetime(2026, 10, 21, 13, 30), "every 30 minutes"),
    ("every two hours", datetime(2026, 10, 21, 15, 0), "every 2 hours"),
    ("every day at 8", datetime(2026, 10, 22, 8, 0), "every day at 8 AM"),
    ("daily at 3 pm", datetime(2026, 10, 21, 15, 0), "every day at 3 PM"),
    ("every morning", datetime(2026, 10, 22, 9, 0), "every day at 9 AM"),
    ("every weekday at 7 am", datetime(2026, 10, 22, 7, 0), "every weekday at 7 AM"),
    ("every monday at 10", datetime(2026, 10, 26, 10, 0), "every Monday at 10 AM"),
    ("every tuesday and thursday at 6 pm", datetime(2026, 10, 22, 18, 0), "every Tuesday and Thursday at 6 PM"),
    ("on weekends at 11", datetime(2026, 10, 24, 11, 0), "every weekend day at 11 AM"),
]


@pytest.mark.parametrize("words,first,said", REPEATING)
def test_a_repeating_one_starts_at_its_next_turn(words, first, said):
    moment, rule = when(words, NOW)
    assert moment == first
    assert spoken_rule(rule) == said


@pytest.mark.parametrize("words", ["sometime", "later", "every month", "every 10 seconds", "on february 30", "2020-01-01T10:00"])
def test_words_that_pin_down_no_moment_are_refused(words):
    with pytest.raises(Unclear):
        when(words, NOW)


def test_a_rule_rolls_to_the_next_day_it_names():
    _, rule = when("every weekday at 9", NOW)
    friday = datetime(2026, 10, 23, 9, 0)
    assert following(rule, friday) == datetime(2026, 10, 26, 9, 0)


def test_said_back_in_full():
    assert spoken(datetime(2026, 10, 21, 16, 30), NOW) == "4:30 PM today"
    assert spoken(datetime(2026, 10, 22, 9, 0), NOW) == "tomorrow at 9 AM"
    assert spoken(datetime(2026, 10, 23, 17, 0), NOW) == "Friday at 5 PM"
    assert spoken(datetime(2026, 11, 21, 18, 0), NOW) == "Saturday 21 November at 6 PM"
