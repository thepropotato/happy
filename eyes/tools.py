"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

from datetime import datetime
from pathlib import Path
from typing import Literal

from langchain_core.tools import tool

from eyes import attention, identifying, ongoing, tabs, titling
from eyes.deciphering import look
from eyes.describing import answered, smaller
from eyes.framing import framed
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

# THE MODEL KNEW IT ON SIGHT, SO THERE IS NOTHING TO HEDGE.
SURE = "That is what is on the screen. Say it plainly."

# IT DID NOT KNOW ON SIGHT, SO WHAT FOLLOWS IS THE WEB'S BEST FIT TO A DESCRIPTION AND NOT
# A THING ANYBODY READ OFF THE SCREEN. NAME IT, AND SAY IN THE SAME BREATH THAT YOU ARE NOT
# SURE, BECAUSE A GUESS HANDED OVER AS A FACT IS THE ONE ANSWER THEY CANNOT CHECK.
GUESS = (
    "None of this was read off the screen: it is what the web makes of a description of "
    "the picture. Give them the likeliest name and say in the same sentence that you are "
    "not certain, for example \"I think it is X, but I am not sure.\" Never state it flat."
)

NOTHING = (
    "Nothing came back. Say what is on the screen and say plainly that you cannot name it, "
    "rather than offering a name nothing here supports."
)

# WHOEVER IS ASKING IS LOOKING AT IT. THERE IS NOTHING TO SEND THEM.
HERE = (
    "Whoever is asking is sat in front of this screen, so there is nowhere to send a "
    "picture of it. Tell them it is right there, or read the screen and say what is on it."
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
def screen(action: str, question: str = "") -> str:
    """The screen in front of this person, read or sent.

    action:
    "read" — the text on it right now, exactly as it appears, layout kept. This
    is the fast, exact one: use it whenever you are asked what is on the screen,
    what a window says, or what an error message is.
    "selection" — only the text they have highlighted, in whichever window has
    focus. Prefer this over "read" when they have selected something and ask
    what it is, what it says, what it means, or say "this" or "that" while
    something is plainly selected. If nothing is selected it says so; ask what
    they meant rather than guessing from the rest of the screen.
    "look" with question — what the screen looks like rather than what it says:
    which window is in front, where something sits, what an icon shows, what
    colour something is, whether a box is ticked. This wakes a second model and
    takes several seconds, so use "read" when the answer is written in words.
    "show" — send a picture of the screen to whoever is asking, for "show me",
    "send", "share", "screenshot". Only works for somebody messaging from
    somewhere else; anybody sat at this machine is already looking at it and it
    says so. Say what they are about to see rather than describing every corner.
    "identify" — what the thing on the screen is called, when the screen does
    not say: who these characters are, what show or film this is, what this
    song, game, painting, plant, car or building is. Use it for any "who is
    this", "who are they", "what is this from", "what am I looking at" where the
    answer is a name rather than something written on the screen. This looks,
    then searches the web for what it saw, so it takes longer than the others
    and it goes online. When a title is written on the screen, "read" already
    has the answer and is faster.

    A video is black to a picture, so on a player "read" returns a title and a
    clock at best; current_activity says what that window is showing. For what
    can be clicked, use list_controls, which asks the application directly."""
    wanted = (action or "").strip().lower()

    if wanted == "read":
        return read_the_screen()

    if wanted == "selection":
        return the_selection()

    if wanted == "look":
        return looked_at(question)

    if wanted == "show":
        return sent_on()

    if wanted == "identify":
        return named(question)

    return reasons.no(
        f"I can read the screen, its selection, look at it, name what is on it or send "
        f"it, not {action}."
    )


def read_the_screen():
    """THE WORDS ON IT, EXACTLY AS THEY SIT."""
    try:
        seen = look(framed(grab()).image)
    except VisionError as problem:
        return reasons.no(str(problem))

    return seen.text[:MAX_CHARS] if seen.text else reasons.no("There is no text on the screen.")


def the_selection():
    """ONLY WHAT THEY PICKED OUT, WHICH IS NEVER EVERYTHING ELSE ON SCREEN WITH IT."""
    from hands.controls import clipboard  # LATE: hands.controls REACHES BACK INTO eyes.

    said = clipboard.selection()

    return said if said else reasons.no(clipboard.NOTHING_SELECTED)


def looked_at(question):
    """WHAT IT LOOKS LIKE, WHICH COSTS A SECOND MODEL AND SEVERAL SECONDS."""
    try:
        shot = grab()
        seen = look(shot.image)
        return answered(smaller(shot.image)[0], seen.text[:MAX_CHARS], question)
    except VisionError as problem:
        return reasons.no(str(problem))


def named(question):
    """WHAT THE THING ON THE SCREEN IS CALLED, WHICH IS A LOOK AND THEN A SEARCH."""
    from hands.web.searching import search  # LATE: eyes REACHES ACROSS INTO hands.

    try:
        shot = grab()
        seen = look(shot.image)
        said = identifying.described(shot.image, seen.text)
    except VisionError as problem:
        return reasons.no(str(problem))

    # THE MODEL KNOWING IT OUTRIGHT IS THE WHOLE ANSWER, AND THE WEB ONLY SLOWS IT DOWN.
    if not identifying.hedged(said):
        return f"{said}\n\n{SURE}"

    # IT DID NOT KNOW, SO WHAT IT SAW BECOMES THE SEARCH THAT MIGHT.
    asking = " ".join(said.split())[:200]
    lines = [f"Looking at it: {said}"]

    try:
        found = search(f"{asking} {question}".strip())
    except Exception:
        found = []

    if found:
        lines.append("\nWhat the web says about that description:")
        lines.extend(f"- {each.title} — {each.summary}"[:300] for each in found)

    elsewhere = identifying.corroborated(shot.image)

    if elsewhere:
        lines.append("\nPages this same picture appears on:")
        lines.extend(f"- {each}" for each in elsewhere)

    if not found and not elsewhere:
        lines.append(f"\n{NOTHING}")

        return "\n".join(lines)

    lines.append(f"\n{GUESS}")

    return "\n".join(lines)


def sent_on():
    """A PICTURE, BUT ONLY TO SOMEBODY WHO IS NOT SAT IN FRONT OF IT."""
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
    to go on, screen with "read" next.

    When what is in front is a web page this gives its address too, and that
    address is the answer to "what am I watching", "what is this", and "send me
    the link" — for the page they are on right now. It is the only thing that
    knows. An address from an earlier turn is a different page they have
    finished with, so never answer today's question with yesterday's link: if
    this does not give you one, say you cannot get it rather than reaching for
    one you have seen before.

    This says what a thing is called and, for a file, never where it is: a
    title is not a path, and the moment you need one, file_in_front answers it.
    Say what the title actually is, the file, the page, the video, the person. A season and
    an episode in it is where they are up to; how much is left is that against
    what the whole thing runs to, which search_web finds."""
    # ONE INVENTORY FOR BOTH HALVES OF THE ANSWER, SO THE TWO CANNOT DISAGREE.
    seen = attention.windows()

    if not seen:
        return reasons.no("Nothing is in front: no application is active on this screen.")

    name, title = seen[0]

    if title:
        shown = titling.showing(name, title)
        more = f', showing "{shown}"' if shown else ""
        # A TITLE NAMES A PAGE AND NEVER SAYS WHERE IT IS. ASKED FOR THE LINK TO WHAT IS ON,
        # THE MODEL USED TO REACH FOR THE NEAREST ADDRESS IT HAD EVER SEEN, WHICH WAS AN OLD ONE.
        where = tabs.front(name)
        at = f" Its address is {where}." if where and not where.startswith("chrome://") else ""

        return f'{name} is in front, and the window is "{title}"{more}.{at}{rest(seen)}'

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

    If nothing comes back, it is not open: search_web for it and open the result
    by its number."""
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


TOOLS = [
    read_image,
    screen,
    current_activity,
    already_open,
    list_open_windows,
]