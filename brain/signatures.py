"""EVERY PROMPT HAPPY HAS, WRITTEN AS WHAT GOES IN AND WHAT MUST COME BACK.

A PROMPT WRITTEN OUT AS PROSE ASKS FOR AN ANSWER AND THEN HOPES; A SIGNATURE NAMES THE
ANSWER'S SHAPE AND WILL NOT ACCEPT ANOTHER. THE PARSING THAT USED TO BE DONE BY HAND AFTER
EVERY CALL — UPPERCASING A WORD AND LOOKING FOR SHOW IN IT, PULLING TWO NUMBERS OUT OF A
SENTENCE — IS THE SIGNATURE'S JOB HERE, AND IT IS THE SAME JOB EVERY TIME.

THE WORDING ITSELF IS NOT REWRITTEN. EVERY DOCSTRING BELOW IS THE PROMPT THAT WAS ALREADY
BEING SENT, MOVED AND NOT REPHRASED, SO WHAT CHANGES IS WHO PARSES THE ANSWER AND NOT WHAT
THE MODEL WAS ASKED."""

import dspy

# THE PICTURE ITSELF, WHICH DSPy CARRIES AS A FIELD LIKE ANY OTHER.
Image = dspy.Image


class Judging(dspy.Signature):
    """Someone said something to a computer. Did they ask to see a page, or ask a question?"""

    said: str = dspy.InputField(desc="what they said")
    wants: str = dspy.OutputField(desc="exactly one word: SHOW or READ")


class Picking(dspy.Signature):
    """This is a screenshot. Every piece of text on it was read by OCR and numbered. Say
    which number is the thing being looked for."""

    screen: Image = dspy.InputField(desc="the screenshot")
    menu: str = dspy.InputField(desc="the numbered pieces of text")
    target: str = dspy.InputField(desc="what is being looked for")
    number: str = dspy.OutputField(desc="the number on its own, or NONE if none of them is it")


class Pointing(dspy.Signature):
    """Find something on a screenshot and give the centre of it in pixels of that image."""

    screen: Image = dspy.InputField(desc="the screenshot")
    width: int = dspy.InputField(desc="how wide the image is, in pixels")
    height: int = dspy.InputField(desc="how tall the image is, in pixels")
    target: str = dspy.InputField(desc="what to find")
    where: str = dspy.OutputField(desc="x,y like 412,300, or NONE if it is not on the screen")


class Asking(dspy.Signature):
    """This is the screen of the computer you are working on. Answer the question about it in
    one or two plain sentences, as if saying them out loud. The OCR text was read off the same
    screen: trust it over your own reading of the letters, and trust your own eyes for
    everything it cannot see — icons, pictures, colours, which window is in front, what is
    where."""

    screen: Image = dspy.InputField(desc="the screenshot")
    text: str = dspy.InputField(desc="what OCR read off the screen")
    question: str = dspy.InputField(desc="the question about the screen")
    answer: str = dspy.OutputField(desc="one or two plain spoken sentences")


class Describing(dspy.Signature):
    """This is a picture from a computer screen. Say what is in it in one short line, in words
    somebody could type into a search box. The OCR text was read off the same picture: a
    title, a channel, a player's caption or a watermark in it names the thing outright, so use
    it when it is there. Say, in this order: what it is from if you can tell (the show, film,
    game, comic or place), then who or what is in it (how many, what they look like, what they
    are wearing or doing), then the style (live action, anime, cartoon, 3D). Name it only if
    you are sure. If you are not sure of the name, describe it and do not guess a name."""

    screen: Image = dspy.InputField(desc="the picture")
    text: str = dspy.InputField(desc="what OCR read off the picture")
    described: str = dspy.OutputField(desc="one line, no more, in words a search box would take")
