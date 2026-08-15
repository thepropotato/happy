"""WHAT IS ACTUALLY TRUE, OUT OF WHAT EVERY SENSE REPORTED."""

import time

from eyes import attention, pointing, structure
from eyes.shapes import Scene, VisionError

# THESE RANK THE SENSES, THEY ARE NOT PROBABILITIES.
TOLD = 0.90  # THE APPLICATION SAID SO.
READ = 0.75  # OCR READ IT OFF THE PIXELS.
PICKED = 0.55  # THE LOOKING MODEL CHOSE IT OUT OF WHAT OCR FOUND.
POINTED = 0.35  # THE LOOKING MODEL GAVE A COORDINATE. LEAST EXACT, LAST RESORT.

# A CLICK NUDGES THE POINTER BY A PIXEL OR TWO ON SOME SETUPS.
DRIFT = 6

# SMALL ENOUGH THAT A BLINKING CURSOR IS NOT A CHANGE, BIG ENOUGH THAT A MENU IS.
THUMB = 64


def scene(words=False):
    """WHAT IS ON THE SCREEN NOW, OUT OF EVERY SENSE WORTH ASKING."""
    return observed(words=words, reading=True)


def glance():
    """THE SAME SCENE WITHOUT EVER READING WORDS."""
    return observed(words=False, reading=False)


def observed(words, reading):
    elements = structure.tree()
    senses = ["structure"] if elements else []
    bare = structure.thin(elements)
    text, mark = "", ""

    if bare or words:
        text, mark = looked(read_words=reading and (bare or words))

        if mark:
            senses.append("pixels")

    name, handle = attention.front()

    return Scene(
        app=name,
        window=attention.window(handle),
        elements=tuple(elements),
        focus=pointing.caret(),
        pointer=pointing.pointer(),
        text=text,
        mark=mark,
        senses=tuple(senses),
        at=time.time(),
    )


def looked(read_words):
    """THE SCREEN FINGERPRINTED, AND ITS WORDS ONLY IF THEY WERE ASKED FOR."""
    from eyes.screen import grab

    try:
        shot = grab()
    except VisionError:
        return "", ""

    mark = fingerprint(shot.image)

    if not read_words:
        return "", mark

    from eyes.deciphering import look

    try:
        return look(shot.image).text, mark
    except VisionError:
        return "", mark


def fingerprint(image):
    """THE SCREEN AS A SHORT STRING, FOR TELLING TWO OF THEM APART."""
    small = image.convert("L").resize((THUMB, THUMB))
    pixels = small.getdata()
    middle = sum(pixels) / len(pixels)

    return "".join("1" if value > middle else "0" for value in pixels)


def shape(scene):
    """A SCENE REDUCED TO WHAT WOULD HAVE TO CHANGE FOR SOMETHING TO HAVE HAPPENED."""
    return (
        scene.app,
        scene.window,
        scene.focus,
        frozenset((each.kind, each.said, each.ticked, each.enabled) for each in scene.elements),
        scene.mark,  # THE PIXELS, NOT THE WORDS: OCR IS TOO SLOW TO RUN TWICE PER CLICK.
    )


def moved(before, after):
    """TRUE WHEN ANYTHING AT ALL IS DIFFERENT BETWEEN TWO SCENES."""
    return shape(before) != shape(after)


def difference(before, after):
    """THE ONE THING MOST WORTH SAYING ABOUT WHAT CHANGED, OR ""."""
    if before.app != after.app:
        return f"{after.app or 'something else'} came to the front"

    if before.window != after.window:
        return f"the window is now {after.window or 'untitled'}"

    was_ticked, now_ticked = ticks(before), ticks(after)

    for name in sorted(was_ticked.keys() & now_ticked.keys()):
        if was_ticked[name] != now_ticked[name]:
            return f"{name} is now {'ticked' if now_ticked[name] else 'not ticked'}"

    was = {each.said for each in before.elements if each.said}
    now = {each.said for each in after.elements if each.said}

    if now - was:
        return "something new appeared"

    if was - now:
        return "some of it went away"

    if before.focus != after.focus and after.focus:
        return f"the keyboard is now in {after.focus}"

    return "the screen changed" if before.mark != after.mark else ""


def ticks(scene):
    """EVERY TICKABLE THING IN A SCENE, BY NAME."""
    return {each.said: each.ticked for each in scene.elements if each.ticked is not None and each.said}


def meddling(after, ours):
    """WHAT THE PERSON DID WHILE HAPPY WAS WORKING, OR None."""
    if not ours:
        return None

    x, y = ours
    here, there = after.pointer

    if abs(here - x) > DRIFT or abs(there - y) > DRIFT:
        return "the mouse was moved"

    return None
