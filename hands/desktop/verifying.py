"""WATCHING AN ACT THROUGH AND JUDGING WHAT IT DID.

expecting SAYS WHAT SHOULD BECOME TRUE. THIS WAITS FOR THE SCREEN TO STOP MOVING,
ASKS THAT QUESTION, GIVES A SLOW WINDOW ONE SECOND CHANCE, AND TURNS THE ANSWER
INTO A SENTENCE SOMEONE CAN HEAR.

IT NEVER RETRIES THE ACT. A CLICK THAT DID NOTHING IS REPORTED AS A CLICK THAT
DID NOTHING, BECAUSE PRESSING AN UNKNOWN BUTTON A SECOND TIME IS HOW ONE FAILURE
BECOMES TWO.
"""

import time
from typing import NamedTuple

import eyes
from eyes import estimating, structure
from hands.desktop import expecting, noticing

# HOW LONG TO WAIT FOR THE SCREEN TO REACT AT ALL, AND THEN FOR WHATEVER STARTED
# TO FINISH. LOOKING COSTS ABOUT A TWELFTH OF A SECOND, SO THESE ARE COUNTED IN
# LOOKS AS MUCH AS IN SECONDS.
STEP_SECONDS = 0.08
REACT_SECONDS = 1.0
SETTLE_SECONDS = 0.6

# ONE MORE LOOK, LATER, BEFORE CALLING SOMETHING A FAILURE. A SLOW WINDOW IS THE
# COMMONEST REASON A GOOD CLICK LOOKS LIKE A BAD ONE, AND WAITING IS CHEAPER AND
# FAR SAFER THAN PRESSING THE THING A SECOND TIME.
PATIENCE_SECONDS = 0.5

BLIND = "I cannot see what is on the screen, so I will not touch anything."


class Done(NamedTuple):
    """WHAT TO SAY ABOUT AN ACT, AND WHETHER IT IS WORTH CARRYING ON AFTER."""

    said: str
    worked: bool


def looking():
    """THE WORLD MODEL AND A FRESH SCENE, OR THE REASON THERE ISN'T ONE.

    THIS GLANCES RATHER THAN READS. AN ACT NEEDS TO KNOW WHAT THE CONTROLS ARE
    AND WHETHER THEY CHANGED, AND NEITHER OF THOSE IS WORTH AN OCR PASS: READING
    THE WHOLE SCREEN COSTS OVER A SECOND AND PUT FIVE SECONDS ON EVERY ACT
    BEFORE THIS SAID glance().
    """
    model = eyes.current()
    scene = model.glance()

    if scene.blind:
        return model, scene, structure.readable() or BLIND

    return model, scene, None


def settled(before):
    """THE SCREEN ONCE IT HAS REACTED AND THEN STOPPED MOVING.

    WAITING FOR IT TO *STOP* IS NOT ENOUGH ON ITS OWN: A WINDOW THAT HAS NOT YET
    STARTED IS ALSO PERFECTLY STILL, AND WOULD BE JUDGED A FAILURE A TENTH OF A
    SECOND BEFORE IT OPENED.
    """
    started = time.perf_counter()
    scene = estimating.glance()

    while not estimating.moved(before, scene):
        if time.perf_counter() - started > REACT_SECONDS:
            return scene

        time.sleep(STEP_SECONDS)
        scene = estimating.glance()

    steady = time.perf_counter()

    while time.perf_counter() - steady < SETTLE_SECONDS:
        time.sleep(STEP_SECONDS)
        again = estimating.glance()

        if not estimating.moved(scene, again):
            return again

        scene = again

    return scene


def judged(expectation, before, after, model):
    """THE VERDICT, GIVING A SLOW WINDOW ONE MORE CHANCE BEFORE CONDEMNING IT."""
    answer = expecting.verdict(expectation, before, after)

    if not answer.ok:
        time.sleep(PATIENCE_SECONDS)
        after = estimating.glance()
        answer = expecting.verdict(expectation, before, after)

    model.update(after)

    return answer, after


def opened(said):
    """A SENTENCE STARTED WITH A CAPITAL."""
    return said[0].upper() + said[1:] if said else said


def lowered(said):
    """THE SAME WORDS PUT BACK INSIDE ANOTHER SENTENCE."""
    return said[0].lower() + said[1:] if said else said


def report(did, answer, after, at, ours=None):
    """WHAT TO SAY: SHORT, PLAIN, AND HONEST ABOUT WHAT WAS NOT CONFIRMED.

    did IS THE ACT WITH NO FULL STOP ON IT, SO IT CAN BE EITHER THE WHOLE
    SENTENCE OR THE FIRST HALF OF ONE THAT GOES ON TO SAY WHAT WENT WRONG.
    """
    said = [f"{did}." if answer.ok else f"I {lowered(did)} but {answer.told}."]

    if answer.ok and answer.sure and answer.told:
        said.append(f"{opened(answer.told)}.")
    elif answer.ok and not answer.sure:
        said.append("I could not confirm it either way.")

    if estimating.meddling(after, ours) or noticing.watch().busy(at):
        said.append("You were using the computer at the same time, so do check it.")

    return Done(" ".join(said), answer.ok)
