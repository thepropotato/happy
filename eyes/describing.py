"""THE MODEL THAT LOOKS."""

import base64
import io
import re

from eyes.shapes import VisionError
from memory import settings

MAX_LABELS = 150

MISSING = (
    "I can read the screen but I cannot look at it yet, {model} is not "
    "installed. Get it with: {how}"
)


def smaller(image):
    """THE PICTURE AT A SIZE WORTH SENDING, AND HOW MUCH IT SHRANK."""
    wide = settings.get("eyes.width")

    if image.width <= wide:
        return image, 1.0

    ratio = wide / image.width

    return image.resize((wide, int(image.height * ratio))), ratio


def packed(image):
    """THE PICTURE AS THE MODEL WANTS IT: BASE64 IN A DATA URL."""
    hold = io.BytesIO()
    image.save(hold, format="PNG")

    return "data:image/png;base64," + base64.b64encode(hold.getvalue()).decode()


def picked(image, menu, target):
    """WHICH NUMBERED PIECE OF TEXT IS THE TARGET, AS THE MODEL SAID IT, OR ''."""
    return said("Picking", "number", screen=image, menu=menu, target=target)


def pointed_at(image, target):
    """WHERE THE TARGET IS, AS THE MODEL SAID IT, OR ''."""
    return said(
        "Pointing", "where",
        screen=image, width=image.width, height=image.height, target=target,
    )


def answered(image, text, question):
    """THE ANSWER TO A QUESTION ABOUT THE SCREEN, IN PLAIN SPOKEN WORDS."""
    return said("Asking", "answer", screen=image, text=text, question=question)


def described(image, text):
    """WHAT THE PICTURE IS, IN WORDS A SEARCH BOX WOULD TAKE, OR ''."""
    return said("Describing", "described", screen=image, text=text)


def signature(name):
    """ONE SIGNATURE BY NAME. LATE, BECAUSE eyes IS IMPORTED WHILE brain IS STILL COMING UP."""
    from brain import signatures

    return getattr(signatures, name)


def said(signature_name, field, screen, **inputs):
    """ONE SIGNATURE ASKED OF THE LOOKING MODEL, AS THE STRING IT ANSWERED WITH.

    A LOOKING MODEL THAT IS NOT THERE IS THE ONE FAILURE WORTH ITS OWN WORDS, BECAUSE THE
    ANSWER IS A COMMAND THE PERSON CAN RUN. EVERY OTHER FAILURE IS THE MODEL SAYING NOTHING,
    AND SAYING "IT IS NOT INSTALLED" ABOUT A MODEL THAT IS SENDS SOMEBODY OFF TO PULL A MODEL
    THEY ALREADY HAVE."""
    from brain import asking, model  # LATE: brain REACHES BACK INTO eyes.

    answer = asking.looked(
        signature(signature_name), screen=asking.picture(screen), **inputs
    )

    if answer is None:
        if missing(asking.trouble):
            raise VisionError(
                MISSING.format(model=model.looking(), how=model.obtain(model.looking()))
            )

        raise VisionError(f"{model.looking()} could not look at it: {asking.trouble}")

    return (getattr(answer, field, "") or "").strip()


def missing(trouble):
    """WHETHER A FAILURE IS THE BACKEND SAYING IT HAS NO SUCH MODEL."""
    return "not found" in (trouble or "").lower()


def listing(seen, limit=MAX_LABELS):
    """THE TEXT ON SCREEN AS A NUMBERED MENU FOR THE MODEL TO PICK FROM."""
    lines = [line for line in seen.lines if line.text.strip()][:limit]

    return lines, "\n".join(f"{number}: {line.text}" for number, line in enumerate(lines))


def digits(answer):
    """THE FIRST WHOLE NUMBER IN AN ANSWER, OR None."""
    found = re.search(r"-?\d+", answer or "")

    return int(found.group()) if found else None


def numbers(answer):
    """THE FIRST PAIR OF NUMBERS IN AN ANSWER, OR None."""
    found = re.findall(r"-?\d+(?:\.\d+)?", answer or "")

    return (float(found[0]), float(found[1])) if len(found) >= 2 else None
