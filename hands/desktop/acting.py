"""ONE ACT, START TO FINISH: LOOK, FIND IT, ASK IF IT MATTERS, DO IT, LOOK
AGAIN, AND SAY WHAT ACTUALLY HAPPENED.

THIS IS THE WHOLE POINT OF THE MODULE. THE OLD WAY WAS TO CLICK AND ASSUME, AND
ASSUMING IS FINE UNTIL A POPUP APPEARS, THE BUTTON IS GREYED OUT, THE WINDOW IS
STILL LOADING, OR SOMEONE ELSE IS USING THE COMPUTER. SO NOTHING HERE REPORTS
SUCCESS IT HAS NOT CHECKED FOR.

THE SCREEN IS READ FRESH EVERY TIME. A MENU THAT OPENED HALF A SECOND LATE MAKES
EVERY REMEMBERED POSITION A LIE, SO IT IS ONE ACT PER CALL AND NEVER A
REMEMBERED BOX.

ANYTHING THAT CAN BE REFUSED WITHOUT LOOKING IS REFUSED WITHOUT LOOKING. A
MISTYPED SHORTCUT USED TO COST A FULL READ OF THE DESKTOP BEFORE ANYONE NOTICED
IT WAS NONSENSE.
"""

import time

import conscience
import eyes
from eyes import estimating
from hands.desktop import expecting, guard, noticing, pointer
from hands.desktop.verifying import Done, judged, looking, report, settled


def clicked(target, times=1, button="left"):
    """CLICK SOMETHING BY NAME, AND CHECK THAT IT DID SOMETHING."""
    model, before, trouble = looking()

    if trouble:
        return Done(trouble, False)

    # ask=False STOPS THE ESCALATION AT OCR. ONE OF THE LOOKING MODEL'S ANSWERS
    # TOOK EIGHTY FOUR SECONDS AND EVICTED THE MODEL THAT HAS TO SPEAK.
    found = eyes.where(target, elements=before.elements, ask=False)

    if found is None:
        return Done(f"I cannot find anything called {target} on the screen.", False)

    element = found.element

    if element is not None and not element.enabled:
        return Done(f"{found.label} is greyed out, so I have not clicked it.", False)

    reason = guard.danger(found.label)

    if reason and not conscience.allowed(f"click {found.label}", reason):
        return Done(conscience.REFUSED, False)

    expectation = expecting.for_click(found)
    at = time.time()

    noticing.watch().start()
    pointer.click(found.x, found.y, times, button)

    answer, after = judged(expectation, before, settled(before), model)

    sure = found.confidence > estimating.POINTED
    did = f"Clicked {found.label}" if sure else f"Clicked where I think {target} is"
    done = report(did, answer, after, at, ours=(found.x, found.y))

    if found.rivals:
        return Done(f"{done.said} Something else here is called {found.label} too.", done.worked)

    return done


def typed(text, into=""):
    """TYPE SOMETHING, OPTIONALLY CLICKING A FIELD FIRST, AND CHECK IT LANDED."""
    if not str(text).strip():
        return Done("There was nothing to type.", False)

    if into:
        first = clicked(into)

        if not first.worked:
            return first

    model, before, trouble = looking()

    if trouble:
        return Done(trouble, False)

    expectation = expecting.for_typing(text)
    at = time.time()

    noticing.watch().start()
    pointer.write(text)

    answer, after = judged(expectation, before, settled(before), model)
    where = f" into {into}" if into else ""

    return report(f'Typed "{expecting.shorten(text)}"{where}', answer, after, at)


def pressed(keys):
    """ONE SHORTCUT, AND WHETHER THE SCREEN ANSWERED IT."""
    complaint = pointer.unknown_keys(keys)

    if complaint:
        return Done(complaint, False)

    reason = guard.danger_keys(keys)

    if reason and not conscience.allowed(f"press {keys}", reason):
        return Done(conscience.REFUSED, False)

    model, before, trouble = looking()

    if trouble:
        return Done(trouble, False)

    expectation = expecting.for_keys(keys)
    at = time.time()

    noticing.watch().start()
    pointer.press(keys)

    answer, after = judged(expectation, before, settled(before), model)

    return report(f"Pressed {keys}", answer, after, at)


def scrolled(direction, amount=1):
    """SCROLL, AND CHECK THAT SOMETHING MOVED."""
    complaint = pointer.unknown_direction(direction)

    if complaint:
        return Done(complaint, False)

    model, before, trouble = looking()

    if trouble:
        return Done(trouble, False)

    expectation = expecting.for_scroll(direction)
    at = time.time()

    noticing.watch().start()
    pointer.scroll(direction, amount)

    answer, after = judged(expectation, before, settled(before), model)

    return report(f"Scrolled {direction}", answer, after, at)
