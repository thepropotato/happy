"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool

from eyes import attention
from eyes.describing import QUESTION, asked, smaller
from face import handing
from hands import asking
from eyes.parts import VisionError
from eyes.reading import look
from eyes.screen import grab

MAX_CHARS = 20000

SHOTS = Path(__file__).resolve().parents[1] / "data" / "shots"

# WHOEVER IS ASKING IS LOOKING AT IT. THERE IS NOTHING TO SEND THEM.
HERE = (
    "Whoever is asking is sat in front of this screen, so there is nowhere to send a "
    "picture of it. Tell them it is right there, or use read_screen and say what is on it."
)


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
        return asking.no(note)

    if where.is_dir():
        return asking.no(f"{where} is a folder, not a picture.")

    try:
        seen = look(where)
    except VisionError as problem:
        return asking.no(str(problem))

    if not seen.text:
        return asking.no(f"{where.name} is a picture, but there are no words in it.")

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
    and also tells you what is greyed out or ticked. If you are asked to show or
    send the screen rather than to say what is on it, use show_screen."""
    try:
        seen = look(grab().image)
    except VisionError as problem:
        return asking.no(str(problem))

    return seen.text[:MAX_CHARS] if seen.text else asking.no("There is no text on the screen.")


@tool
def current_activity() -> str:
    """What this person is doing on the computer right now: the application they
    are in front of, and the title of the window they have open in it.

    Use this whenever you are asked what they are doing, what they are up to,
    what they are working on, whether they are busy, or asked to tell somebody
    else any of that. Never answer those out of your own head. There is no way
    to know what somebody is doing without looking, and "on the computer" tells
    whoever asked nothing they had not already guessed.

    The window title is usually the specific thing: the file being edited, the
    page being read, the video playing, the person being written to. Say what it
    actually is, in a way that means something to whoever asked. If the title is
    too little to go on, read_screen next and say what is really happening."""
    seen = attention.doing()

    if not seen:
        return asking.no("Nothing is in front: no application is active on this screen.")

    if "window is" in seen:
        return f"{seen}."

    # A REFUSED ACCESSIBILITY PROMPT LOOKS EXACTLY LIKE A WINDOW WITH NO NAME, AND
    # ONE OF THE TWO IS SOMETHING THE PERSON CAN ACTUALLY GO AND FIX.
    return f"{seen}. {attention.allowed() or 'Its window has no title.'}"


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
        return asking.no(str(problem))


@tool
def show_screen() -> str:
    """Send a picture of the screen to whoever is asking, so they can look at it
    themselves. Use this when you are asked to show, send, share or screenshot
    the screen, or asked what it looks like by somebody who cannot see it.

    This only works for somebody messaging Happy from somewhere else. Anybody
    sat at this machine is already looking at the screen, and this will say so
    rather than send anything.

    The picture goes with your answer, so say what they are about to see rather
    than describing every corner of it. read_screen is still the way to answer a
    question about what the screen says."""
    if not handing.wanted():
        return asking.no(HERE)

    try:
        shot = grab()
    except VisionError as problem:
        return asking.no(str(problem))

    SHOTS.mkdir(parents=True, exist_ok=True)
    where = SHOTS / f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
    shot.image.save(where)

    if not handing.offer(where):
        where.unlink(missing_ok=True)

        return asking.no("They have already been sent a picture of the screen this turn.")

    return f"A picture of the whole screen, {shot.image.width} by {shot.image.height}, is on its way."


TOOLS = [read_image, read_screen, current_activity, look_at_screen, show_screen]
