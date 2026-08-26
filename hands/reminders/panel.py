"""EVERY REMINDER AS ONE ROW, FOR SOMEBODY WHO WOULD RATHER LOOK THAN ASK."""

from heart import rules, wording
from memory import reminders
from memory.kinds import action, folded, heading, state

DROP = "drop"

SWEEP = "sweep"

NONE = "reminders.none"

CLEAR = "reminders.clear"

EMPTY = "Nothing set"

NOTHING = 'Say "remind me to call the dentist at four" and it will be here, with the time he made of it.'

UPCOMING = "Upcoming"

DONE = "Done"

# WHAT A ROW SAYS BESIDE THE NAME, WHICH IS THE ONE THING WORTH SEEING WITHOUT OPENING IT.
TODAY = "%H:%M"

OTHER = "%-d %b"

RUNS = "Runs the routine"


def rows():
    """WAITING ONES OVER FINISHED ONES, EACH UNDER A HEADING THAT COUNTS THEM."""
    at = rules.now()
    waiting = reminders.waiting()
    finished = reminders.done()

    if not waiting and not finished:
        return [state(NONE, EMPTY, "", NOTHING)]

    shown = []

    if waiting:
        shown.append(heading(UPCOMING, len(waiting)))
        shown.extend(one(each, at) for each in waiting)

    if finished:
        shown.append(heading(DONE, len(finished)))
        shown.extend(one(each, at) for each in finished)
        shown.append(action(CLEAR, "Clear done", SWEEP, "Clear", "Every finished one, gone."))

    return shown


def one(found, at):
    """A ROW THAT OPENS INTO WHEN IT IS FOR AND WHERE IT CAME FROM, AND A WAY TO BE RID OF IT."""
    return folded(key(found), found["what"], marked(found, at), inside(found, at))


def key(found):
    return f"reminders.{found['id']}"


def inside(found, at):
    when = at.fromtimestamp(found["due"], at.tzinfo)
    repeats = wording.repeatedly(found["rule"], when)
    said = [
        ("when", "Went off" if found["done"] else "When", wording.spoken(when, at), None),
        ("repeats", "Repeats", repeats, None),
        ("runs", RUNS, found["what"] if found["kind"] == reminders.ROUTINE else "", None),
        ("said", "Asked as", found["said"], None),
        ("fired", "Gone off", counted(found["fired"]), None),
    ]

    shown = [
        state(f"{key(found)}.{name}", label, says, hint)
        for name, label, says, hint in said if says
    ]

    return shown + [action(key(found), "Forget it", DROP, "Forget", "Gone for good.")]


def marked(found, at):
    """THE WHEN, SHORT ENOUGH TO SIT BESIDE THE NAME."""
    if found["rule"]:
        return shortly(found["rule"])

    when = at.fromtimestamp(found["due"], at.tzinfo)

    return when.strftime(TODAY if when.date() == at.date() else OTHER)


SHORT = {3600: "hourly", 86400: "daily"}


def shortly(rule):
    """A RECURRENCE IN AS FEW LETTERS AS IT CAN BE SAID IN."""
    parts = str(rule).split()

    if parts[0] == rules.EVERY:
        seconds = int(parts[1])

        return SHORT.get(seconds) or f"every {wording.lasting(seconds)}"

    if parts[0] == rules.WEEKLY:
        return wording.DAYS[int(parts[1])][:3]

    return parts[0]


def counted(fired):
    return "" if not fired else "once" if fired == 1 else f"{fired} times"


def forget(name):
    """WHAT THE FORGET BUTTON ASKS FOR. THE KEY IT SENDS CARRIES THE ROW'S NUMBER."""
    said = str(name or "")
    number = said[len("reminders."):] if said.startswith("reminders.") else said

    return reminders.forget(int(number)) if number.isdigit() else None


def clear():
    """WHAT THE CLEAR BUTTON ASKS FOR: EVERYTHING THAT HAS BEEN AND GONE."""
    return reminders.sweep()
