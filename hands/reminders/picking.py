"""WHICH REMINDER SOMEBODY MEANT, AND THE WORDS FOR WHEN IT IS NOT ONE."""

from hands import reasons
from heart import wording
from memory import reminders

NONE = "Nothing is set."

WHICH = "Which reminder do you mean?"

NOTHING = 'I have not got a reminder about "{said}".'

INSTEAD = " There is {kept}."

SEVERAL = "That could be {kept}. Which one?"

# HOW MANY ARE WORTH READING OUT WHEN SOMEBODY ASKS FOR ONE THAT IS NOT THERE.
FEW = 4

# SHORTER THAN THIS AND FINDING IT INSIDE A LONGER REMINDER MEANS NOTHING.
LEAST = 3


def plain(said):
    return "".join(each for each in str(said or "").lower() if each.isalnum() or each == " ").strip()


def matched(said):
    """EVERY REMINDER SOMEBODY COULD HAVE MEANT, WAITING ONES BEFORE FINISHED ONES."""
    wanted = plain(said)

    if not wanted:
        return []

    kept = reminders.waiting() + reminders.done()
    exact = [each for each in kept if plain(each["what"]) == wanted]

    if exact:
        return exact

    return [
        each for each in kept
        if len(wanted) > LEAST and (wanted in plain(each["what"]) or plain(each["what"]) in wanted)
    ]


def only(said):
    """THE ONE MEANT, OR THE WORDS SAYING WHY THERE IS NOT ONE.

    ONE THAT MATCHES SEVERAL IS READ BACK RATHER THAN GUESSED AT: MOVING OR DROPPING THE
    WRONG REMINDER IS A THING DONE THAT NOBODY ASKED FOR."""
    if not str(said or "").strip():
        found = reminders.last()

        return (found, None) if found else (None, reasons.no(WHICH + otherwise()))

    found = matched(said)

    if not found:
        return None, reasons.no(NOTHING.format(said=said) + otherwise())

    if len(found) > 1:
        return None, reasons.no(SEVERAL.format(kept=listed(found)))

    return found[0], None





def otherwise():
    """WHAT THERE IS INSTEAD, SO A NO IS NEVER ONLY A NO."""
    kept = reminders.waiting()

    if not kept:
        return f" {NONE}"

    return INSTEAD.format(kept=listed(kept))


def listed(kept):
    return " or ".join(f'"{each["what"]}"' for each in kept[:FEW])


def described(kept, at=None):
    """A RUN OF REMINDERS IN THE WORDS SOMEBODY WOULD HEAR THEM IN."""
    return ". ".join(wording.briefly(each, at) for each in kept)
