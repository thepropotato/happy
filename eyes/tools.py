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

# WINDOWS DEEP ENOUGH TO NAME. PAST THIS IS A LIST NOBODY COULD BE READ OUT LOUD.
MOST = 12

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
    else any of that. "What am I doing" is that question. "What are you doing"
    is not: that one is about you, and nothing on their screen answers it.
    Never answer out of your own head. There is no way to know what somebody is
    doing without looking, and "on the computer" tells whoever asked nothing
    they had not already guessed.

    Use it just as much when the question never says the word screen but cannot
    be answered without it: how much of this is left, what the next one is, how
    far in they are, which one this is. Those are about what they are in front
    of right now, so they start here, every time, before you count anything.

    This is the front window only, and what somebody is doing is often behind
    it. If what came back is not what you were asked about — the wrong
    application, a call, Happy himself — do not answer from it and do not give
    up: list_open_windows has everything else they have open.

    The window title is usually the specific thing: the file being edited, the
    page being read, the video playing, the person being written to. Say what it
    actually is, in a way that means something to whoever asked. If the title is
    too little to go on, read_screen next and say what is really happening."""
    seen = attention.doing()

    if not seen:
        return asking.no("Nothing is in front: no application is active on this screen.")

    if "window is" in seen:
        return f"{seen}.{rest()}"

    # A REFUSED ACCESSIBILITY PROMPT LOOKS EXACTLY LIKE A WINDOW WITH NO NAME, AND
    # ONE OF THE TWO IS SOMETHING THE PERSON CAN ACTUALLY GO AND FIX.
    return f"{seen}. {attention.allowed() or 'Its window has no title.'}{rest()}"


def rest():
    """WHAT ELSE IS OPEN, NAMED HERE RATHER THAN FETCHED BY A SECOND CALL.

    POINTING AT THE OTHER TOOL WAS TRIED AND FOLLOWED ONE TIME IN FOUR: THE
    MODEL READS ONE WINDOW TITLE, TAKES IT FOR THE ANSWER, AND STOPS. SO THE
    QUESTION IS ANSWERED WHOLE IN ONE ROUND TRIP INSTEAD, BECAUSE A CHAIN THAT
    HAS TO BE FOLLOWED THREE TIMES OUT OF FOUR IS NOT A CHAIN THAT WORKS.
    """
    behind = attention.windows()[1:MOST]

    if not behind:
        return ""

    listed = "; ".join(f'{name} — "{title}"' if title else name for name, title in behind)

    return f" Also open behind it, front to back: {listed}."


@tool
def list_open_windows() -> str:
    """Every window this person has open right now, front to back, each with the
    application it is in and its own title.

    What somebody is doing is not only the window on top. A video plays on
    behind the thing being typed into, a chat sits open two windows back, a
    download finishes somewhere nobody has looked in an hour. current_activity
    hands you the front one and nothing else, so come here whenever what you
    were asked about is not in it, whenever you were asked what else is open or
    running, and whenever the front window turns out to be Happy or a call.

    The titles are the part that means anything: the file, the page, the
    episode, the person being written to. Read the whole list before answering,
    and name the real thing rather than the application it happens to be in."""
    seen = attention.windows()[:MOST]

    if not seen:
        return asking.no(
            f"Nothing is open: no ordinary window is on this screen. "
            f"{attention.allowed() or ''}".strip()
        )

    listed = "\n".join(f'{name} — "{title}"' if title else name for name, title in seen)

    return f"Open right now, front to back:\n{listed}"


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


TOOLS = [
    read_image,
    read_screen,
    current_activity,
    list_open_windows,
    look_at_screen,
    show_screen,
]
