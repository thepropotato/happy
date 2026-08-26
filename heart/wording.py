"""A MOMENT SAID THE WAY A PERSON SAYS ONE, BECAUSE ALL OF THIS ENDS UP SPOKEN."""

from datetime import timedelta

from heart import rules

HALVES = ((12, "in the morning"), (17, "in the afternoon"), (22, "in the evening"))

NAMED = {(0, 0): "midnight", (12, 0): "noon"}

WITHIN = 7  # PAST THIS A WEEKDAY STOPS MEANING ANYTHING AND IT WANTS THE DATE.

REPEATS = {
    "daily": "every day at {clock}",
    "weekdays": "every weekday at {clock}",
    "weekends": "every weekend at {clock}",
    "weekly": "every {day} at {clock}",
}

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

SPANS = ((86400, "day"), (3600, "hour"), (60, "minute"), (1, "second"))


def spoken(when, at=None):
    """THE WHOLE MOMENT: THE CLOCK FACE AND THE DAY, WHICH IS WHAT MAKES IT CHECKABLE."""
    return f"{clock(when)}, {daily(when, at or rules.now())}"


def clock(when):
    """4 in the morning, 4:30 in the afternoon, midnight."""
    named = NAMED.get((when.hour, when.minute))

    if named:
        return named

    hour = when.hour % 12 or 12
    minute = f":{when.minute:02d}" if when.minute else ""

    return f"{hour}{minute} {half(when.hour)}"


def half(hour):
    for edge, said in HALVES:
        if hour < edge:
            return said

    return "at night"


def daily(when, at):
    """today, tomorrow, on Friday, on 21 May."""
    days = (when.date() - at.date()).days

    if days == 0:
        return "today"

    if days == 1:
        return "tomorrow"

    if days == -1:
        return "yesterday"

    if 0 < days < WITHIN:
        return f"on {DAYS[when.weekday()]}"

    return f"on {when.day} {when.strftime('%B')}"


def repeatedly(rule, when=None):
    """A RECURRENCE IN WORDS: every hour, every day at 8 in the evening."""
    parts = str(rule or "").split()

    if not parts:
        return ""

    if parts[0] == rules.EVERY:
        return f"every {lasting(int(parts[1]))}"

    said = REPEATS.get(parts[0], "")
    hour, minute = (int(each) for each in parts[-1].split(":"))
    face = clock(when.replace(hour=hour, minute=minute)) if when else parts[-1]

    return said.format(clock=face, day=DAYS[int(parts[1])] if parts[0] == "weekly" else "")


def lasting(seconds):
    """1800 AS half an hour, 3600 AS hour, 7200 AS 2 hours."""
    if seconds == 1800:
        return "half an hour"

    for size, said in SPANS:
        if seconds >= size and not seconds % size:
            count = seconds // size

            return said if count == 1 else f"{count} {said}s"

    return f"{seconds} seconds"


def briefly(found, at=None):
    """ONE REMINDER IN A LINE, FOR A LIST SOMEBODY IS HEARING RATHER THAN READING."""
    at = at or rules.now()
    when = at.fromtimestamp(found["due"], at.tzinfo)
    said = repeatedly(found["rule"], when) if found["rule"] else spoken(when, at)

    return f"{said} — {found['what']}"


def away(seconds):
    """HOW LONG UNTIL SOMETHING, FOR A PANEL ROW RATHER THAN A SENTENCE."""
    if seconds < 60:
        return "any moment"

    return f"in {lasting(int(seconds) - int(seconds) % 60)}"
