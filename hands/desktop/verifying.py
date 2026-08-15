"""WATCHING AN ACT THROUGH AND JUDGING WHAT IT DID."""

import time
from typing import NamedTuple

import eyes
from eyes import agreeing, structure
from hands.desktop import expecting, noticing

# HOW LONG TO WAIT FOR THE SCREEN TO REACT, AND THEN FOR WHATEVER STARTED TO FINISH.
STEP_SECONDS = 0.08
REACT_SECONDS = 1.0
SETTLE_SECONDS = 0.6

# A SLOW WINDOW IS THE COMMONEST REASON A GOOD CLICK LOOKS LIKE A BAD ONE.
PATIENCE_SECONDS = 0.5

BLIND = "I cannot see what is on the screen, so I will not touch anything."


class Done(NamedTuple):
    """WHAT TO SAY ABOUT AN ACT, AND WHETHER IT IS WORTH CARRYING ON AFTER."""

    said: str
    worked: bool


def looking():
    """THE WORLD MODEL AND A FRESH SCENE, OR THE REASON THERE ISN'T ONE."""
    model = eyes.current()
    scene = model.glance()

    if scene.blind:
        return model, scene, structure.readable() or BLIND

    return model, scene, None


def settled(before):
    """THE SCREEN ONCE IT HAS REACTED AND THEN STOPPED MOVING."""
    started = time.perf_counter()
    scene = agreeing.glance()

    while not agreeing.moved(before, scene):
        if time.perf_counter() - started > REACT_SECONDS:
            return scene

        time.sleep(STEP_SECONDS)
        scene = agreeing.glance()

    steady = time.perf_counter()

    while time.perf_counter() - steady < SETTLE_SECONDS:
        time.sleep(STEP_SECONDS)
        again = agreeing.glance()

        if not agreeing.moved(scene, again):
            return again

        scene = again

    return scene


def judged(expectation, before, after, model):
    """THE VERDICT, GIVING A SLOW WINDOW ONE MORE CHANCE BEFORE CONDEMNING IT."""
    answer = expecting.verdict(expectation, before, after)

    if not answer.ok:
        time.sleep(PATIENCE_SECONDS)
        after = agreeing.glance()
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
    """WHAT TO SAY: SHORT, PLAIN, AND HONEST ABOUT WHAT WAS NOT CONFIRMED."""
    said = [f"{did}." if answer.ok else f"I {lowered(did)} but {answer.told}."]

    if answer.ok and answer.sure and answer.told:
        said.append(f"{opened(answer.told)}.")
    elif answer.ok and not answer.sure:
        said.append("I could not confirm it either way.")

    if agreeing.meddling(after, ours) or noticing.watch().busy(at):
        said.append("You were using the computer at the same time, so do check it.")

    return Done(" ".join(said), answer.ok)
