"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

from langchain_core.tools import tool
from typing import Literal

from hands import reasons
from hands.reminders import picking
from hands.reminders.picking import NONE
from heart import resolving, wording
from memory import reminders, routines

SET = "Set. {said}."

MOVED = "Moved. {said}."

# ONLY WHERE NOBODY SAID WHICH HALF OF THE DAY. THE TIME WAS TAKEN THE SOONEST WAY ROUND
# AND THIS IS THE ONE CHANCE ANYBODY GETS TO SAY IT WAS THE OTHER WAY.
CHECK = " Say if you meant {other}."

MORNING = "the morning"

AFTERNOON = "the afternoon"

AGAIN = "Right. Again {said}."

UNKNOWN = 'There is no routine called "{name}", so there is nothing for that to run.'


def remind_me(what: str, when: str, routine: str = "") -> str:
    """Set a reminder. Use it whenever the person wants telling about something later —
    "remind me to drink water every hour", "remind me to call the dentist at four",
    "renew the parking on the twenty first".

    what is the thing itself, in the fewest words that still make sense read out on
    their own hours from now. "call the dentist", "take your tablets". Not a sentence about
    reminding, and never your own words for something they said plainly.

    when is their own words for the time, handed over exactly as they said them. Do
    not work out a date and do not write a timestamp. You are not told what day it is
    or what the time is, so anything you work out yourself will be wrong. "at four",
    "every hour", "tomorrow at nine", "on the twenty first", "in twenty minutes" all
    go through as they were said.

    routine is for when they want one of their own saved routines to go off at a time
    rather than a line said back to them — "run my morning brief every day at seven".
    Put the routine's name in it and leave what empty. Leave it empty otherwise, which
    is almost always: a plain reminder is words, not a job.

    What comes back says the time it actually set, in full. Say that back to them.
    It is the only chance they get to catch a time that was read the wrong way round."""
    moment, complaint = resolving.moment(when)

    if complaint:
        return reasons.no(complaint)

    if routine.strip():
        return standing(routine, moment, when)

    made = reminders.save(what, moment["due"], said=when, rule=moment["rule"])

    if made is None:
        return reasons.no("A reminder needs something to remind you of.")

    return SET.format(said=wording.briefly(made)) + invited(moment)


def my_reminders() -> str:
    """What the person has asked to be reminded of, soonest first, with the time each
    one is set for. Use it whenever they ask what is set, what is coming up, or
    whether something is still on. This changes nothing."""
    kept = reminders.waiting()

    return picking.described(kept) if kept else NONE


def change_reminder(which: str = "", when: str = "", what: str = "") -> str:
    """Change a reminder that is already set. Use it when they want a different time
    for one — "make that four in the afternoon", "move the dentist one to six in the
    evening" — or different words for it.

    which names the reminder by what it is about, in their words. Leave it empty when
    they mean the one just set or the one just being talked about.

    when is their words for the new time, handed over exactly as said, the same as
    remind_me. Leave it empty when only the wording is changing."""
    found, complaint = picking.only(which)

    if complaint:
        return complaint

    if what.strip():
        found = reminders.reword(found["id"], what) or found

    if not when.strip():
        return MOVED.format(said=wording.briefly(found))

    moment, complaint = resolving.moment(when)

    if complaint:
        return reasons.no(complaint)

    moved = reminders.move(found["id"], moment["due"], rule=moment["rule"], said=when)

    return MOVED.format(said=wording.briefly(moved)) + invited(moment)


def forget_reminder(which: str) -> str:
    """Drop a reminder for good. Use it when they have actually asked for one to go —
    "forget that reminder", "stop reminding me to drink water". Stopping a repeating
    one is this, not a change."""
    found, complaint = picking.only(which)

    if complaint:
        return complaint

    gone = reminders.forget(found["id"])

    return f'Forgotten. No more "{gone["what"]}".'


def snooze_reminder(when: str = "in ten minutes", which: str = "") -> str:
    """Set a reminder to come round again a little later. Use it the moment they say
    "remind me again in ten minutes", "not now", or "in a bit" after one has just gone
    off — and for one that has not gone off yet when they want another nudge as well
    as the one already set.

    when is their words for how much later, handed over exactly as said. Where they
    only said to remind them again and gave no time, leave it alone.

    which names the reminder, in their words. Leave it empty for the one that has just
    gone off, which is nearly always what they mean.

    This adds a fresh one and never touches the times of anything already set, so
    snoozing a repeating reminder leaves it repeating on its own schedule."""
    found, complaint = picking.only(which)

    if complaint:
        return complaint

    moment, complaint = resolving.moment(when)

    if complaint:
        return reasons.no(complaint)

    made = reminders.save(found["what"], moment["due"], said=when, kind=found["kind"])

    return AGAIN.format(said=wording.briefly(made)) + invited(moment)


def standing(name, moment, said):
    """A SAVED ROUTINE SET TO GO OFF ON ITS OWN, WHICH IS THE OTHER HALF OF WHAT A ROUTINE IS.

    THE NAME IS CHECKED NOW RATHER THAN AT SEVEN IN THE MORNING, WHEN NOBODY IS THERE TO BE
    TOLD THERE IS NO SUCH ROUTINE."""
    kept = routines.one(name)

    if kept is None:
        return reasons.no(UNKNOWN.format(name=name))

    made = reminders.save(
        kept["name"], moment["due"], said=said, rule=moment["rule"], kind=reminders.ROUTINE
    )

    return SET.format(said=wording.briefly(made)) + invited(moment)


def invited(when):
    """THE INVITATION TO CORRECT A HALF OF THE DAY NOBODY ACTUALLY NAMED."""
    if when["sure"]:
        return ""

    other = AFTERNOON if when["when"].hour < 12 else MORNING

    return CHECK.format(other=other)



ACTIONS = Literal["set", "list", "change", "forget", "snooze"]


@tool
def reminder(action: ACTIONS, what: str = "", when: str = "", which: str = "", routine: str = "") -> str:
    """Reminders. "set" with what ("call the dentist", the thing itself in few
    words) and when (their exact words for the time, "at four", "every hour",
    "tomorrow at nine"; never a date you worked out, you are not told the day).
    "list" says what is set. "change" with which (the reminder in their words, or
    empty for the one just mentioned) and a new when or what. "forget" with which.
    "snooze" with when ("in ten minutes") for the one that just went off. routine
    names a saved routine to run at that time instead of words. What comes back
    says the time it actually set: say it back, it is their one chance to correct
    a wrong half of the day."""
    if action == "set":
        return remind_me(what, when, routine)

    if action == "list":
        return my_reminders()

    if action == "change":
        return change_reminder(which, when, what)

    if action == "forget":
        return forget_reminder(which)

    return snooze_reminder(when or "in ten minutes", which)


TOOLS = [reminder]
