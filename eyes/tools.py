"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

from langchain_core.tools import tool

from eyes.describing import QUESTION, asked, smaller
from eyes.parts import VisionError
from eyes.reading import look
from eyes.screen import grab

MAX_CHARS = 20000


@tool
def read_image(path: str) -> str:
    """Read the words inside a picture: a screenshot, a photo of a screen or a
    sign, a scanned page, or anything else where the text is part of the image
    rather than in the file. Accepts a full path like "~/Desktop/shot.png", or
    just a name like "screenshot" or "the receipt photo", in which case it finds
    the picture first.

    Use this whenever you are asked what a picture says or shows in words. Do
    not say you cannot see images."""
    from hands import files  # LATE: files HANDS PICTURES BACK HERE.

    where, note = files.locate(path)

    if where is None:
        return note

    if where.is_dir():
        return f"{where} is a folder, not a picture."

    try:
        seen = look(where)
    except VisionError as problem:
        return str(problem)

    if not seen.text:
        return f"{where.name} is a picture, but there are no words in it."

    header = f"{note}\n" if note else ""

    return f"{header}{seen.text[:MAX_CHARS]}"


@tool
def read_screen() -> str:
    """Read the text that is on the screen right now, exactly as it appears,
    with the layout kept. Use this whenever you are asked what is on the screen,
    what a window says, what an error message is, or what the user is looking
    at. This is fast and exact, so prefer it over look_at_screen whenever the
    answer is written on the screen in words.

    If what you actually want is what can be clicked, use list_controls instead.
    It asks the application directly, which is several times faster than this
    and also tells you what is greyed out or ticked."""
    try:
        seen = look(grab().image)
    except VisionError as problem:
        return str(problem)

    return seen.text[:MAX_CHARS] if seen.text else "There is no text on the screen."


@tool
def look_at_screen(question: str) -> str:
    """Ask about what the screen looks like, rather than what it says: which
    window is in front, where something sits, what an icon or a picture shows,
    what colour something is, whether a box is ticked. Give the question you
    want answered.

    This wakes a second model and takes several seconds, so use read_screen
    instead when the answer is text that is written on the screen."""
    try:
        shot = grab()
        seen = look(shot.image)
        about = QUESTION.format(text=seen.text[:MAX_CHARS], question=question)

        return asked(smaller(shot.image)[0], about)
    except VisionError as problem:
        return str(problem)


TOOLS = [read_image, read_screen, look_at_screen]
