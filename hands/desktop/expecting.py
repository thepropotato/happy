"""WHAT SHOULD BE TRUE AFTER AN ACT, AND WHETHER IT TURNED OUT TO BE.

AN ACT THAT IS NOT CHECKED IS AN ASSUMPTION, AND THE ASSUMPTION IS WRONG EXACTLY
WHEN IT MATTERS: THE BUTTON THAT WAS GREYED OUT, THE DIALOG THAT STOLE THE
KEYBOARD, THE PERSON WHO CLICKED SOMEWHERE ELSE HALF A SECOND AGO. SO EVERY ACT
SAYS WHAT IT EXPECTS BEFORE IT HAPPENS, AND THE ANSWER IS CHECKED AFTER.

A CHECK MAY COME BACK None, WHICH IS NOT FAILURE. IT MEANS NOTHING WE CAN SENSE
WOULD HAVE CHANGED EITHER WAY, AND SAYING SO IS BETTER THAN INVENTING A VERDICT.
"""

from pathlib import Path
from typing import NamedTuple

from eyes import estimating
from eyes.finding import ENTRY


class Expectation(NamedTuple):
    """WHAT AN ACT PROMISED, AND HOW TO FIND OUT."""

    says: str
    check: object  # (before, after) -> True, False, OR None WHEN IT CANNOT TELL.


class Verdict(NamedTuple):
    ok: bool
    sure: bool  # False WHEN NOTHING COULD TELL US EITHER WAY.
    told: str


def named(scene, label):
    """THE ELEMENT IN A SCENE THAT GOES BY THIS NAME, OR None."""
    wanted = (label or "").strip().lower()

    for element in scene.elements:
        if element.said.strip().lower() == wanted:
            return element

    return None


def holding(scene, text):
    """TRUE WHEN SOMETHING ON THE SCREEN NOW CONTAINS THIS TEXT."""
    wanted = " ".join(text.split()).strip().lower()

    if not wanted:
        return False

    for element in scene.elements:
        if wanted in " ".join((element.value or "").split()).lower():
            return True

    return wanted in " ".join(scene.text.split()).lower() if scene.text else False


def stirred(before, after):
    """THE WEAKEST USEFUL CHECK: DID ANYTHING AT ALL HAPPEN."""
    return estimating.moved(before, after)


def for_click(found):
    """WHAT A CLICK ON THIS THING SHOULD DO.

    A CHECKBOX IS THE ONE CASE WE CAN CHECK EXACTLY, BECAUSE THE APPLICATION
    REPORTS THE TICK. EVERYTHING ELSE IS "THE SCREEN SHOULD NOT BE IDENTICAL",
    WHICH IS WEAK BUT CATCHES THE FAILURE THAT ACTUALLY HAPPENS: NOTHING.
    """
    element = found.element

    if element is not None and element.ticked is not None:
        label, was = element.said, element.ticked

        def flipped(before, after):
            now = named(after, label)

            return None if now is None or now.ticked is None else now.ticked != was

        return Expectation(
            f"{label} should end up {'not ticked' if was else 'ticked'}", flipped
        )

    # CLICKING SOMEWHERE TO TYPE CHANGES NOTHING A GLANCE CAN SEE: A CARET IN AN
    # EMPTY BOX MOVES NO PIXELS, AND A BOX THAT ALREADY HELD THE KEYBOARD NONE.
    if element is not None and element.kind in ENTRY:
        label = element.said

        def caught(before, after):
            return None if not after.focus else settled(after.focus, label)

        return Expectation(f"the keyboard should end up in {label}", caught)

    # THE KEYBOARD LANDING IN THE THING WE PRESSED IS A YES ON ITS OWN, AND THE
    # ONLY ONE AVAILABLE WHEN THAT THING ALREADY HELD THE CARET.
    label = found.label

    def landed(before, after):
        if after.focus and settled(after.focus, label):
            return True

        return stirred(before, after)

    return Expectation(f"the screen should change after clicking {found.label}", landed)


def settled(focus, label):
    """TRUE WHEN THE KEYBOARD IS IN THE THING WE MEANT. THE CARET IS REPORTED BY
    WHATEVER NAME THE APPLICATION GIVES IT, WHICH IS NOT ALWAYS THE NAME THE
    ELEMENT CARRIED: A BOX LABELLED FOR ITS PLACEHOLDER ANSWERS TO EITHER."""
    here, wanted = focus.strip().lower(), (label or "").strip().lower()

    return here == wanted or here in wanted or wanted in here


def for_typing(text):
    """TYPED TEXT SHOULD BE SOMEWHERE ON THE SCREEN AFTERWARDS."""

    def arrived(before, after):
        if holding(after, text):
            return True

        # AN APP THAT DESCRIBES NOTHING LEAVES ONLY "DID ANY PIXEL MOVE".
        return None if not after.senses or after.blind else stirred(before, after)

    return Expectation(f'"{shorten(text)}" should appear where the keyboard was', arrived)


def for_attaching(name):
    """A PASTED FILE SHOWS ITSELF: A PREVIEW, A ROW, A CHIP WITH ITS NAME ON IT.

    THE NAME IS TRIED WITHOUT ITS ENDING TOO, BECAUSE A MESSAGE APP OFTEN DRAWS
    THE PREVIEW WITH THE KIND OF FILE WRITTEN OUT SEPARATELY FROM THE NAME.
    """

    def arrived(before, after):
        if holding(after, name) or holding(after, Path(name).stem):
            return True

        return None if not after.senses or after.blind else stirred(before, after)

    return Expectation(f"{name} should appear where it was pasted", arrived)


def for_keys(keys):
    return Expectation(f"the screen should change after pressing {keys}", stirred)


def for_scroll(direction):
    return Expectation(f"the screen should move when scrolling {direction}", stirred)


def shorten(text, limit=40):
    said = " ".join(str(text).split())

    return said if len(said) <= limit else said[:limit] + "..."


def verdict(expectation, before, after):
    """WHETHER REALITY DID WHAT WAS EXPECTED OF IT."""
    try:
        answer = expectation.check(before, after)
    except Exception:
        answer = None

    happened = estimating.difference(before, after)

    if answer is None:
        return Verdict(True, False, happened or "nothing I can see changed")

    return Verdict(bool(answer), True, happened or "nothing on the screen changed")
