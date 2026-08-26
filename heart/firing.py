"""WHAT HAPPENS WHEN ONE COMES DUE. THE ONLY PART THAT SAYS ANYTHING OUT LOUD."""

from heart import rules, wording
from memory import reminders

# ON TIME. NOTHING IS ASKED OF A MODEL FOR THIS, SO THE WORDS ARE OURS AND ARE FIXED.
REMINDER = "Reminder. {what}"

# LATE ENOUGH TO BE WORTH SAYING SO, BUT STILL THE SAME DAY'S BUSINESS.
LATE = "This was for {when}. {what}"

# HE WAS NOT RUNNING. THIS IS AN ACCOUNT OF WHAT WENT BY, NOT A REMINDER — IT IS TOO LATE
# TO BE ONE, AND PRETENDING OTHERWISE WOULD BE WORSE THAN SAYING NOTHING.
ASLEEP = "You had me switched off, so I could not get to {these} — {said}. Hope you got to {them}."

MORE = " {count} more are in the panel as well."

MISSING = 'That reminder wanted a routine called "{name}", and there is not one by that name any more.'

# HOW LATE IS STILL WORTH SAYING PLAINLY RATHER THAN APOLOGISING FOR.
SOON = 120

# AND HOW MANY OF THEM GET READ OUT IN FULL BEFORE THE REST ARE ONLY COUNTED.
FEW = 4


def due(saying, at=None):
    """EVERYTHING THAT HAS COME ROUND, SAID AND SEEN TO. HOW MANY WENT OFF."""
    at = at or rules.now()
    gone = 0

    for found in reminders.overdue(at.timestamp()):
        fire(found, saying, at)
        gone += 1

    return gone


def fire(found, saying, at):
    said = going(found)
    behind = at.timestamp() - found["due"]

    if behind > SOON:
        when = at.fromtimestamp(found["due"], at.tzinfo)
        saying(LATE.format(when=wording.spoken(when, at), what=said))
    else:
        saying(REMINDER.format(what=said))

    roll(found, at)

    # SO THAT "REMIND ME AGAIN IN TEN MINUTES" HAS SOMETHING TO MEAN.
    reminders.handled(found["id"])


def going(found):
    """THE WORDS ONE REMINDER GOES OFF WITH: ITS OWN, OR WHAT ITS ROUTINE CAME BACK WITH."""
    if found["kind"] != reminders.ROUTINE:
        return found["what"]

    from brain import running
    from memory import routines

    kept = routines.one(found["what"])

    if kept is None:
        return MISSING.format(name=found["what"])

    routines.ran(kept["name"])

    return running.run(kept, kept["name"])


def roll(found, at):
    """A ONE OFF IS DONE. A REPEATING ONE GOES ROUND TO ITS NEXT TIME.

    THE NEXT TIME IS WORKED OUT FROM NOW RATHER THAN FROM WHEN IT WAS DUE, SO A LAPTOP THAT
    WAS SHUT FOR TWO DAYS DOES NOT COME BACK TO FORTY OF THEM STACKED UP."""
    if not found["rule"]:
        reminders.finished(found["id"])

        return

    when = rules.after(found["rule"], at)

    if when is None:
        reminders.finished(found["id"])
    else:
        reminders.rolled(found["id"], when.timestamp())


def missed(saying, at=None):
    """WHAT WENT BY WHILE HAPPY WAS OFF, IN ONE THING SAID RATHER THAN ONE EACH."""
    at = at or rules.now()
    late = [each for each in reminders.overdue(at.timestamp() - SOON)]

    for found in [each for each in late if each["rule"]]:
        roll(found, at)  # A REPEATING ONE JUST PICKS UP AGAIN. FORTY OF THEM IS NOT NEWS.

    ones = [each for each in late if not each["rule"]]

    if not ones:
        return 0

    saying(accounted(ones, at))

    for found in ones:
        reminders.finished(found["id"])

    return len(ones)


def accounted(ones, at):
    """THE ONE SENTENCE THEY ARE ALL SAID IN, WITH THE OVERFLOW COUNTED RATHER THAN READ."""
    many = len(ones) > 1
    said = ". ".join(wording.briefly(each, at) for each in ones[:FEW])
    line = ASLEEP.format(
        these="these" if many else "this",
        said=said,
        them="them" if many else "it",
    )

    rest = len(ones) - FEW

    if rest > 0:
        line += MORE.format(count=rest)

    return line
