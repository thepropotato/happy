"""WHAT IS ACTUALLY TRUE, OUT OF WHAT EVERY SENSE REPORTED.

A SCREENSHOT IS ONE OBSERVATION, NOT THE STATE. THE APPLICATION'S OWN
DESCRIPTION OF ITSELF IS ANOTHER, AND A BETTER ONE. THIS FILE PUTS THEM
TOGETHER, SAYS HOW SURE THE ANSWER IS, AND ANSWERS THE ONE QUESTION EVERYTHING
DOWNSTREAM ACTUALLY ASKS: *WHAT CHANGED?*

THE CHEAP SENSES RUN EVERY TIME AND THE EXPENSIVE ONES ONLY WHEN THE CHEAP ONES
CAME BACK EMPTY. AN APPLICATION THAT DESCRIBES ITSELF COSTS A TENTH OF A SECOND;
READING ITS PIXELS INSTEAD COSTS A SECOND AND A HALF.
"""

import time

from eyes import attention, structure
from eyes.parts import Scene, VisionError

# HOW MUCH A SOURCE IS WORTH BELIEVING. THESE RANK THE SENSES, THEY ARE NOT
# PROBABILITIES: A MODEL POINTING AT A PIXEL IS THE WORST ANSWER WE WILL STILL
# ACT ON. MULTIPLYING THEM TOGETHER WOULD MANUFACTURE A PRECISION NOBODY
# MEASURED.
TOLD = 0.90  # THE APPLICATION SAID SO.
READ = 0.75  # OCR READ IT OFF THE PIXELS.
PICKED = 0.55  # THE LOOKING MODEL CHOSE IT OUT OF WHAT OCR FOUND.
POINTED = 0.35  # THE LOOKING MODEL GAVE A COORDINATE. LEAST EXACT, LAST RESORT.

# HOW FAR THE POINTER MAY DRIFT FROM WHERE WE LEFT IT AND STILL BE WHERE WE LEFT
# IT. A CLICK NUDGES IT BY A PIXEL OR TWO ON SOME SETUPS.
DRIFT = 6

# HOW SMALL THE PICTURE GOES BEFORE IT IS FINGERPRINTED. SMALL ENOUGH THAT A
# CURSOR BLINKING IS NOT A CHANGE, BIG ENOUGH THAT AN OPENED MENU IS.
THUMB = 64


def scene(words=False):
    """WHAT IS ON THE SCREEN NOW, OUT OF EVERY SENSE WORTH ASKING.

    THE PICTURE IS TAKEN ONLY WHEN THE APPLICATION REFUSED TO DESCRIBE ITSELF,
    OR WHEN THE WORDS WERE ASKED FOR OUTRIGHT. ASKING COSTS A SIXTH OF A SECOND,
    A PICTURE A QUARTER, AND READING ONE A SECOND AND A HALF.
    """
    return observed(words=words, reading=True)


def glance():
    """THE SAME SCENE WITHOUT EVER READING WORDS. THIS IS WHAT VERIFICATION USES.

    A CLICK HAS TO BE CHECKED THE MOMENT IT LANDS, AND TWO OCR PASSES AROUND
    EVERY CLICK WOULD PUT THREE SECONDS ON EVERY ACT. THE FINGERPRINT ANSWERS
    "DID ANYTHING HAPPEN" FOR A QUARTER OF A SECOND.
    """
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
        focus=attention.caret(),
        pointer=attention.pointer(),
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
    except VisionError:  # NO PERMISSION TO SEE. THE STRUCTURE STILL ANSWERED.
        return "", ""

    mark = fingerprint(shot.image)

    if not read_words:
        return "", mark

    from eyes.reading import look

    try:
        return look(shot.image).text, mark
    except VisionError:
        return "", mark


def fingerprint(image):
    """THE SCREEN AS A SHORT STRING, FOR TELLING TWO OF THEM APART.

    THIS IS THE ONLY CHANGE DETECTION LEFT WHEN AN APPLICATION DESCRIBES NOTHING
    AND OCR IS TOO SLOW TO RUN TWICE ROUND EVERY CLICK.
    """
    small = image.convert("L").resize((THUMB, THUMB))
    pixels = small.getdata()
    middle = sum(pixels) / len(pixels)

    return "".join("1" if value > middle else "0" for value in pixels)


def shape(scene):
    """A SCENE REDUCED TO WHAT WOULD HAVE TO CHANGE FOR SOMETHING TO HAVE
    HAPPENED. POSITIONS ARE LEFT OUT: A WINDOW SHUFFLING TWO PIXELS IS NOT AN
    EVENT, A BUTTON APPEARING IS."""
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
    """THE ONE THING MOST WORTH SAYING ABOUT WHAT CHANGED, OR "".

    ONE THING, NOT A LIST. THIS ENDS UP SPOKEN, AND A SENTENCE THAT RUNS
    "THE WINDOW IS NOW DOCUMENTS, AND ONE THING APPEARED, AND NINE THINGS WENT
    AWAY" IS NOBODY'S IDEA OF BEING TOLD WHAT HAPPENED.
    """
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

    # COUNTED, NOT NAMED, AND NOT NUMBERED EITHER: "FORTY EIGHT THINGS WENT
    # AWAY" IS A TRUE SENTENCE THAT NO ONE WOULD EVER SAY OUT LOUD.
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
    """WHAT THE PERSON DID WHILE HAPPY WAS WORKING, OR None.

    ours IS WHERE HAPPY LEFT THE POINTER. FINDING IT SOMEWHERE ELSE MEANS A HAND
    ON THE MOUSE, WHICH IS THE ONE THING NO AMOUNT OF LOOKING AT THE SCREEN
    WOULD HAVE TOLD US.
    """
    if not ours:
        return None

    x, y = ours
    here, there = after.pointer

    if abs(here - x) > DRIFT or abs(there - y) > DRIFT:
        return "the mouse was moved"

    return None
