"""THE SOONEST FUTURE MOMENT THE WORDS COULD MEAN, WHICH IS THE WHOLE OF THE RULE."""

import calendar
from datetime import datetime, timedelta

from heart import reading, rules
from heart.words import beyond

MIDNIGHT = (0, 0)

# HOW MANY DAYS OF CANDIDATES ARE WORTH BUILDING FOR AN UNPINNED DAY. TWO COVERS EVERY
# CLOCK FACE, BECAUSE ONE OF THEM COMES ROUND WITHIN TWENTY FOUR HOURS.
NEARBY = 2

# AND HOW MANY MONTHS, FOR A BARE DAY OF THE MONTH THAT NOT EVERY MONTH HAS.
SPREAD = 4

VAGUE = (
    'I could not work out a time from "{said}". Say it as a clock time or a date — "at half '
    "four\", \"tomorrow at nine\", \"on the twenty first\", \"every hour\"."
)

WONT = (
    'I do not trust myself with "{words}" — it means different things to different people. '
    "Give me the day or the date itself and I will not get it wrong."
)


def moment(said, at=None):
    """WHEN THOSE WORDS MEAN, AS (when, complaint). when CARRIES THE RULE IF IT REPEATS."""
    at = at or rules.now()

    if not str(said or "").strip():
        return None, VAGUE.format(said=said)

    refused = beyond(said)

    if refused:
        return None, WONT.format(words=" ".join(refused))

    found = reading.parts(said)

    if found["rest"]:
        return None, VAGUE.format(said=said)

    return built(found, at, said)


def built(found, at, said):
    if found["offset"]:
        return settled(at + timedelta(seconds=found["offset"]), "", found), None

    if found["every"]:
        rule = rules.written(rules.EVERY, seconds=found["every"])

        return settled(at + timedelta(seconds=found["every"]), rule, found), None

    if found["repeat"]:
        return repeating(found, at, said)

    # in three days WITH NO CLOCK IS AN OFFSET, NOT A DAY WITH A MIDNIGHT ON IT.
    if found["shifted"] and not found["clocks"]:
        return settled(at + timedelta(days=found["days"]), "", found), None

    when = soonest(found, at)

    if when is None:
        return None, VAGUE.format(said=said)

    return settled(when, "", found), None


def repeating(found, at, said):
    """every day at eight. THE CLOCK IS RESOLVED ONCE AND THEN THE RULE HOLDS IT."""
    clock = pick(found, at)
    kind = rules.WEEKLY if found["repeat"] == "weekly" else found["repeat"]
    rule = rules.written(kind, clock=clock, weekday=found["weekday"] or 0)
    when = rules.after(rule, at)

    if when is None:
        return None, VAGUE.format(said=said)

    return settled(when, rule, found), None


def pick(found, at):
    """WHICH CLOCK FACE A REPEATING ONE SETTLES ON, BY THE SAME SOONEST RULE."""
    if not found["clocks"]:
        return MIDNIGHT

    if len(found["clocks"]) == 1:
        return found["clocks"][0]

    when = soonest(found, at)

    return (when.hour, when.minute) if when else found["clocks"][0]


def soonest(found, at):
    """THE EARLIEST MOMENT AFTER at THAT MATCHES EVERY PART OF WHAT WAS SAID."""
    clocks = found["clocks"] or [MIDNIGHT]
    ahead = [
        planted(day, clock, at)
        for day in days(found, at)
        for clock in clocks
    ]

    return min([each for each in ahead if each is not None and each > at], default=None)


def planted(day, clock, at):
    """A CLOCK FACE PUT ON A DAY, IN THIS ZONE. NEVER SECONDS ADDED TO AN INSTANT."""
    try:
        return datetime.combine(day, datetime.min.time(), at.tzinfo).replace(
            hour=clock[0], minute=clock[1]
        )
    except ValueError:
        return None


def days(found, at):
    """EVERY DAY THE WORDS COULD HAVE MEANT, SOONEST FIRST."""
    if found["date"]:
        return dated(found["date"], at)

    if found["weekday"] is not None:
        ahead = (found["weekday"] - at.weekday()) % 7

        return [at.date() + timedelta(days=ahead), at.date() + timedelta(days=ahead + 7)]

    if found["days"] is not None:
        return [at.date() + timedelta(days=found["days"])]

    return [at.date() + timedelta(days=each) for each in range(NEARBY)]


def dated(date, at):
    """A DAY OF A MONTH, ROLLED FORWARD UNTIL IT IS AHEAD RATHER THAN BEHIND."""
    month, day = date

    if month:
        return [
            datetime(year, month, day).date()
            for year in (at.year, at.year + 1)
            if day <= calendar.monthrange(year, month)[1]
        ]

    # NOBODY NAMED A MONTH, SO IT IS THE NEXT ONE WITH THAT MANY DAYS IN IT.
    found = []

    for ahead in range(SPREAD):
        year, which = shifted(at.year, at.month, ahead)

        if day <= calendar.monthrange(year, which)[1]:
            found.append(datetime(year, which, day).date())

    return found


def shifted(year, month, ahead):
    """THE MONTH ahead MONTHS ON, WITH THE YEAR IT LANDS IN."""
    whole = (month - 1) + ahead

    return year + whole // 12, whole % 12 + 1


def settled(when, rule, found):
    return {
        "due": when.timestamp(),
        "when": when,
        "rule": rule,
        # WHETHER THEY ACTUALLY SAID WHICH HALF OF THE DAY, WHICH DECIDES WHETHER THE
        # ANSWER INVITES A CORRECTION OR JUST CONFIRMS.
        "sure": len(found["clocks"]) != 2,
    }
