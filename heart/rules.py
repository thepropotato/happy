"""A RECURRENCE, WRITTEN IN WALL CLOCK, AND WHEN IT COMES ROUND NEXT."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

EVERY = "every"

DAILY = "daily"

WEEKDAYS = "weekdays"

WEEKENDS = "weekends"

WEEKLY = "weekly"

WORKING = (0, 1, 2, 3, 4)

RESTING = (5, 6)

# HOW FAR AHEAD A CLOCK RULE IS WILLING TO LOOK BEFORE IT GIVES UP, WHICH IS LONGER THAN
# ANY OF THEM ACTUALLY NEEDS.
REACH = 400

# THE ZONE ONCE IT HAS BEEN WORKED OUT, WHICH IS NOT FREE ON EVERY SYSTEM.
kept = None


def here():
    """THIS MACHINE'S ZONE BY NAME, SO A FUTURE LOCAL TIME SURVIVES A CLOCK CHANGE.

    WINDOWS ANSWERS WITH ITS OWN NAME FOR A ZONE RATHER THAN THE ONE zoneinfo KNOWS, SO THE
    FALLBACK IS THE OFFSET IN USE RIGHT NOW — RIGHT UNTIL THE NEXT TIME THE CLOCKS GO.

    A REAL ZONE IS KEPT, BECAUSE READING IT COSTS A PROCESS ON WINDOWS AND THIS IS ASKED ON
    EVERY TICK. THE CLOCKS GOING IS STILL HANDLED, ZoneInfo KNOWING ITS OWN DATES; ONLY
    CARRYING THE MACHINE TO ANOTHER ZONE WANTS A RESTART. THE FALLBACK IS A FIXED OFFSET AND
    SO IS NEVER KEPT."""
    global kept

    if kept is not None:
        return kept

    from hands.apps import whereabouts

    name = whereabouts.zone()

    if name:
        try:
            kept = ZoneInfo(name)

            return kept
        except Exception:
            pass

    return datetime.now().astimezone().tzinfo


def now():
    return datetime.now(here())


def written(kind, clock=None, weekday=None, seconds=None):
    """A RULE AS IT IS STORED: WALL CLOCK, NEVER AN OFFSET FROM A UTC INSTANT."""
    if kind == EVERY:
        return f"{EVERY} {int(seconds)}"

    said = f"{clock[0]:02d}:{clock[1]:02d}"

    return f"{WEEKLY} {weekday} {said}" if kind == WEEKLY else f"{kind} {said}"


def after(rule, moment):
    """THE NEXT TIME A RULE COMES ROUND, STRICTLY AFTER moment. None IF IT DOES NOT."""
    parts = str(rule or "").split()

    if not parts:
        return None

    kind = parts[0]

    if kind == EVERY:
        return moment + timedelta(seconds=int(parts[1]))

    weekday = int(parts[1]) if kind == WEEKLY else None
    hour, minute = (int(each) for each in parts[-1].split(":"))
    here = moment.astimezone(moment.tzinfo)

    for ahead in range(REACH):
        day = (here + timedelta(days=ahead)).date()

        if not wanted(kind, weekday, day.weekday()):
            continue

        # BUILT AS A LOCAL WALL CLOCK TIME AND THEN GIVEN ITS ZONE, SO EIGHT IN THE MORNING
        # STAYS EIGHT IN THE MORNING THE WEEK THE CLOCKS GO.
        found = datetime.combine(day, datetime.min.time(), moment.tzinfo).replace(
            hour=hour, minute=minute
        )

        if found > moment:
            return found

    return None


def wanted(kind, weekday, day):
    if kind == DAILY:
        return True

    if kind == WEEKDAYS:
        return day in WORKING

    if kind == WEEKENDS:
        return day in RESTING

    return day == weekday
