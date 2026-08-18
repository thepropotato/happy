"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

from datetime import datetime
from pathlib import Path
from typing import Literal

from langchain_core.tools import tool

from eyes import attention, ongoing
from eyes.deciphering import look
from eyes.describing import QUESTION, asked, smaller
from eyes.screen import grab
from eyes.shapes import VisionError
from face import handing
from hands import reasons

MAX_CHARS = 20000

# WINDOWS DEEP ENOUGH TO NAME. PAST THIS IS A LIST NOBODY COULD BE READ OUT LOUD.
MOST = 12

# THE ONE THING THIS FIELD IS ALLOWED TO SAY, THE SAME TWO WORDS open_url TAKES.
SEEING = "show"

CHECKING = "read"

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
        return reasons.no(note)

    if where.is_dir():
        return reasons.no(f"{where} is a folder, not a picture.")

    try:
        seen = look(where)
    except VisionError as problem:
        return reasons.no(str(problem))

    if not seen.text:
        return reasons.no(f"{where.name} is a picture, but there are no words in it.")

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
        return reasons.no(str(problem))

    return seen.text[:MAX_CHARS] if seen.text else reasons.no("There is no text on the screen.")


@tool
def read_selection() -> str:
    """The exact text currently highlighted, in whichever window has focus.

    Use this whenever they have selected or highlighted something and ask what
    it is, what it says, what it means, to explain it, translate it or
    summarise it, or say "this" or "that" while something is plainly selected.
    Prefer this over read_screen and look_at_screen for that: it reads exactly
    what they picked out rather than everything else on screen with it. If
    nothing is selected, say so and ask what they meant instead of guessing
    from the rest of the screen."""
    from hands.controls import clipboard  # LATE: hands.controls REACHES BACK INTO eyes.

    said = clipboard.selection()

    return said if said else reasons.no(clipboard.NOTHING_SELECTED)


@tool
def current_activity() -> str:
    """What this person is doing right now: the application in front of them and
    the title of its window.

    Use this whenever you are asked what they are doing, are up to, are working
    on, or whether they are busy, and whenever you are asked to tell somebody
    else any of that. Use it too when the question never says the word screen
    but cannot be answered without looking: how much of this is left, what the
    next one is, how far in they are, which one this is.

    "What am I doing" is this question. "What are you doing" is not — that one
    is about you, and nothing on their screen answers it.

    This names the window in front and everything else open behind it, on this
    desktop and on every other one, so a show playing fullscreen somewhere else
    is in the answer too. Read past the first window before you answer: what
    they asked about is often one of the ones behind it. already_open also
    reads browser tabs, which no window title shows. When a title is too little
    to go on, read_screen next.

    This says what a thing is called and never where it is. A title is a name,
    not a path, and a name is no use to anything that has to open, read, send or
    attach the thing, or run a command inside the project it belongs to. The
    moment that is what you are doing, file_in_front is the one that answers it.
    Working a path out yourself from a name in a title is making one up.

    The title is usually the specific thing: the file, the page, the video, the
    person being written to. Say what it actually is. It often carries a season
    and an episode, or a page and a chapter — that is where they are up to, not
    how much is left. How much is left is that minus what the whole thing runs
    to, and search_web is where the total comes from. Work it out rather than
    saying you cannot."""
    # ONE INVENTORY FOR BOTH HALVES OF THE ANSWER, SO THE TWO CANNOT DISAGREE.
    seen = attention.windows()

    if not seen:
        return reasons.no("Nothing is in front: no application is active on this screen.")

    name, title = seen[0]

    if title:
        return f'{name} is in front, and the window is "{title}".{rest(seen)}'

    # A REFUSED ACCESSIBILITY PROMPT LOOKS EXACTLY LIKE A WINDOW WITH NO NAME, AND
    # ONE OF THE TWO IS SOMETHING THE PERSON CAN ACTUALLY GO AND FIX.
    return f"{name} is in front. {attention.allowed() or 'Its window has no title.'}{rest(seen)}"


def rest(seen):
    """WHAT ELSE IS OPEN, NAMED HERE RATHER THAN FETCHED BY A SECOND CALL."""
    # windows() PUTS THE FRONT ONE FIRST BY ASKING WHO IS IN FRONT, SO THIS DROPS IT.
    behind = seen[1:MOST]

    if not behind:
        return ""

    listed = "; ".join(f'{name} — "{title}"' if title else name for name, title in behind)

    return f" Also open, on this desktop and any other: {listed}."


@tool
def list_open_windows() -> str:
    """Every window open right now, the one in front first, each with its
    application and its own title. This covers every desktop, not only the one
    being looked at, so a show playing fullscreen on another one is in here.

    Use this when you were asked what else is open or running, and when what you
    were asked about is not the front window: a video plays on behind the thing
    being typed into, a chat sits two windows back. To ask whether one
    particular thing is open, use already_open instead — it also reads browser
    tabs, which this cannot see.

    Read the whole list before answering, and name the real thing rather than
    the application it happens to be in."""
    seen = attention.windows()[:MOST]

    if not seen:
        return reasons.no(
            f"Nothing is open: no ordinary window is on this screen. "
            f"{attention.allowed() or ''}".strip()
        )

    listed = "\n".join(f'{name} — "{title}"' if title else name for name, title in seen)

    return f"Open right now, the one in front first:\n{listed}"


@tool
def already_open(about: str, because: Literal[SEEING, CHECKING]) -> str:
    """Check whether the thing you are about to do is already going on this
    computer. Give what it is about in a few words, for example "Game of
    Thrones", "the spreadsheet", "Gmail".

    Call this first, before you open, start, play or search for anything. A show
    is usually already paused in a tab, a document is usually already open in
    the editor, and carrying on with it is what the person meant by "resume",
    "carry on", "go back to" or "put it back on". Starting a second copy of
    something they already have open is the wrong answer.

    This reads every window and every browser tab, on this desktop and on every
    other one, so it sees pages no window title mentions and shows playing
    fullscreen somewhere else. It only looks, and nothing here moves.

    "because" takes one of two words and nothing else. Say "show" when they
    asked for the thing itself — to watch it, resume it, carry on with it, put
    it back on — and finding it is not the job: call bring_to_front afterwards
    with a few words of its title, then play_pause. Say "read" when they only
    asked you something and their screen should stay exactly where it is: which
    show this is, how far in they are, whether a thing is open. Answer them out
    of what comes back and leave their screen alone. Asking about something is
    not asking to be shown it.

    If nothing comes back, it is not open: search_web for it and open the address
    that came back with it. Do not go straight to open_url with an address you
    wrote yourself out of what they called it."""
    if not about.strip():
        return "Say what to look for."

    found = ongoing.matches(about)

    if found:
        listed = "\n".join(found[:MOST])
        after = (
            "Call bring_to_front to put it in front of them."
            if because == SEEING
            else "They did not ask to be shown it, so answer them from this and move nothing."
        )

        return (
            f"{listed}\n\nThis is only what is open, not what is playing. Nothing has "
            f"moved on their screen. {after}"
        )

    rest_of_it = ongoing.everything()

    if not rest_of_it:
        return f"Nothing about {about} is open, and neither is anything else."

    listed = "\n".join(rest_of_it)

    return f"Nothing about {about} is open. What is open:\n{listed}"


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
        return reasons.no(str(problem))


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
        return reasons.no(HERE)

    try:
        shot = grab()
    except VisionError as problem:
        return reasons.no(str(problem))

    SHOTS.mkdir(parents=True, exist_ok=True)
    where = SHOTS / f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
    shot.image.save(where)

    if not handing.offer(where):
        where.unlink(missing_ok=True)

        return reasons.no("They have already been sent a picture of the screen this turn.")

    return f"A picture of the whole screen, {shot.image.width} by {shot.image.height}, is on its way."


TOOLS = [
    read_image,
    read_screen,
    read_selection,
    current_activity,
    already_open,
    list_open_windows,
    look_at_screen,
    show_screen,
]