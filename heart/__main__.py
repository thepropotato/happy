"""EVERY TIME PHRASE THIS UNDERSTANDS, AND WHAT IT MAKES OF IT: python -m heart

    python -m heart                 the whole table, checked
    python -m heart "at half four"  one phrase, read against the real clock

THE CLOCK IS THE ONE THING HERE THAT CANNOT BE CHECKED BY READING IT, SO THE TABLE IS
THE TEST. now IS FIXED AT A WEDNESDAY LUNCHTIME AND EVERY ROW IS WHAT A PERSON WOULD
SAY OUT LOUD.
"""

import sys
from datetime import datetime

from heart import resolving, rules, wording

SHAPE = "%a %d %b %Y %H:%M"

NOW = datetime(2026, 8, 26, 13, 0)

NO = "no"

# said, THE MOMENT IT COMES TO, AND THE RULE IF IT REPEATS.
TABLE = [
    ("at 4", "Wed 26 Aug 2026 16:00", ""),
    ("at 4pm", "Wed 26 Aug 2026 16:00", ""),
    ("at 4am", "Thu 27 Aug 2026 04:00", ""),
    ("at 11", "Wed 26 Aug 2026 23:00", ""),
    ("at 12", "Thu 27 Aug 2026 00:00", ""),
    ("at 4:30", "Wed 26 Aug 2026 16:30", ""),
    ("at 16:00", "Wed 26 Aug 2026 16:00", ""),
    ("at noon", "Thu 27 Aug 2026 12:00", ""),
    ("at midnight", "Thu 27 Aug 2026 00:00", ""),
    ("in 20 minutes", "Wed 26 Aug 2026 13:20", ""),
    ("in half an hour", "Wed 26 Aug 2026 13:30", ""),
    ("in an hour", "Wed 26 Aug 2026 14:00", ""),
    ("in 3 days", "Sat 29 Aug 2026 13:00", ""),
    ("in 3 days at 9am", "Sat 29 Aug 2026 09:00", ""),
    ("today at 6pm", "Wed 26 Aug 2026 18:00", ""),
    ("tomorrow", "Thu 27 Aug 2026 00:00", ""),
    ("tomorrow at 8", "Thu 27 Aug 2026 08:00", ""),
    ("tomorrow at 8pm", "Thu 27 Aug 2026 20:00", ""),
    ("tomorrow morning at 8", "Thu 27 Aug 2026 08:00", ""),
    ("tonight at 9", "Wed 26 Aug 2026 21:00", ""),
    ("on friday", "Fri 28 Aug 2026 00:00", ""),
    ("friday at 6", "Fri 28 Aug 2026 06:00", ""),
    ("wednesday at 5pm", "Wed 26 Aug 2026 17:00", ""),
    ("wednesday at 9am", "Wed 02 Sep 2026 09:00", ""),
    ("on may 21", "Fri 21 May 2027 00:00", ""),
    ("on 21 may", "Fri 21 May 2027 00:00", ""),
    ("may 21 at 4", "Fri 21 May 2027 04:00", ""),
    ("the 21st", "Mon 21 Sep 2026 00:00", ""),
    ("the 27th", "Thu 27 Aug 2026 00:00", ""),
    ("the 31st", "Mon 31 Aug 2026 00:00", ""),
    ("every hour", "Wed 26 Aug 2026 14:00", "every 3600"),
    ("hourly", "Wed 26 Aug 2026 14:00", "every 3600"),
    ("every 30 minutes", "Wed 26 Aug 2026 13:30", "every 1800"),
    ("every half hour", "Wed 26 Aug 2026 13:30", "every 1800"),
    ("every day at 8pm", "Wed 26 Aug 2026 20:00", "daily 20:00"),
    ("every day at 8am", "Thu 27 Aug 2026 08:00", "daily 08:00"),
    ("every weekday at 9am", "Thu 27 Aug 2026 09:00", "weekdays 09:00"),
    ("every monday at 9am", "Mon 31 Aug 2026 09:00", "weekly 0 09:00"),
    ("next friday", NO, ""),
    ("at bedtime", NO, ""),
    ("sometime later", NO, ""),
    ("a quarter past four", NO, ""),
]


def checked():
    at = NOW.replace(tzinfo=rules.here())
    wrong = 0

    for said, expected, rule in TABLE:
        when, complaint = resolving.moment(said, at)
        got = when["when"].strftime(SHAPE) if when else NO
        amiss = got != expected or (when and when["rule"] != rule)

        wrong += bool(amiss)

        print(f"{'✗' if amiss else ' '} {said:<24} {got:<22} {(when or {}).get('rule', '')}")

        if amiss:
            print(f"{'':<27}want {expected:<22} {rule}")

    print(f"\n{len(TABLE) - wrong}/{len(TABLE)}")

    return wrong


def one(said):
    at = rules.now()
    when, complaint = resolving.moment(said, at)

    if not when:
        print(complaint)

        return 1

    repeats = wording.repeatedly(when["rule"], when["when"])
    print(f"{when['when'].strftime(SHAPE)}   {repeats or wording.spoken(when['when'], at)}")

    return 0


asked = " ".join(sys.argv[1:])

raise SystemExit(one(asked) if asked else checked())
