"""THE MODEL THAT LOOKS.

OCR SAYS WHAT THE WORDS ARE AND EXACTLY WHERE, AND IS BLIND TO EVERYTHING ELSE:
AN ICON, A CHECKBOX, WHICH WINDOW IS IN FRONT. THE MODEL SEES ALL OF THAT AND IS
BAD AT COORDINATES, SO IT IS ASKED TO PICK FROM WHAT OCR ALREADY LOCATED.
"""

import base64
import io
import re

from eyes.parts import VisionError

# HOW WIDE THE PICTURE GOES TO THE LOOKING MODEL. A FULL RETINA GRAB IS MEGABYTES
# OF BASE64 AND MOSTLY EMPTY DESKTOP, AND EVERY ONE OF THOSE BYTES IS TIME.
VLM_WIDTH = 1512

# HOW MANY LINES OF SCREEN TEXT THE MODEL IS OFFERED AT ONCE.
MAX_LABELS = 150

PICK = (
    "This is a screenshot. Every piece of text on it was read by OCR and "
    "numbered:\n\n{menu}\n\n"
    "Which number is: {target}\n"
    "Answer with the number on its own. If none of them is it, answer NONE."
)

POINT = (
    "This is a screenshot, {width} pixels wide and {height} tall. "
    "Find: {target}\n"
    "Answer with the centre of it as two numbers, x and y, in pixels of this "
    "image, like 412,300. Nothing else. If it is not on the screen, answer NONE."
)

QUESTION = (
    "This is the screen of the computer you are working on. Answer the question "
    "about it in one or two plain sentences, as if saying them out loud.\n\n"
    "The text below was read off the same screen by OCR. Trust it over your own "
    "reading of the letters, and trust your own eyes for everything it cannot "
    "see: icons, pictures, colours, which window is in front, what is where.\n\n"
    "{text}\n\nQuestion: {question}"
)

MISSING = (
    "I can read the screen but I cannot look at it yet, {model} is not "
    "installed. Get it with: {how}"
)


def smaller(image):
    """THE PICTURE AT A SIZE WORTH SENDING, AND HOW MUCH IT SHRANK."""
    if image.width <= VLM_WIDTH:
        return image, 1.0

    ratio = VLM_WIDTH / image.width

    return image.resize((VLM_WIDTH, int(image.height * ratio))), ratio


def packed(image):
    """THE PICTURE AS THE MODEL WANTS IT: BASE64 IN A DATA URL."""
    hold = io.BytesIO()
    image.save(hold, format="PNG")

    return "data:image/png;base64," + base64.b64encode(hold.getvalue()).decode()


def asked(image, question):
    """ONE QUESTION ABOUT ONE PICTURE, ANSWERED BY THE LOOKING MODEL."""
    from langchain_core.messages import HumanMessage

    from brain import model  # LATE: brain REACHES BACK INTO hands FOR THE APPS.

    message = HumanMessage(
        content=[
            {"type": "text", "text": question},
            {"type": "image_url", "image_url": {"url": packed(image)}},
        ]
    )

    try:
        return model.sight().invoke([message]).text.strip()
    except Exception as error:
        said = model.reason(error)

        if "not found" in said.lower():  # THE SERVER IS UP, THE MODEL IS NOT THERE.
            raise VisionError(
                MISSING.format(model=model.VISION_MODEL, how=model.obtain(model.VISION_MODEL))
            )

        raise VisionError(f"{model.VISION_MODEL} could not look at it: {said}")


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
