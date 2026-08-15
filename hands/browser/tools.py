"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

import time
from typing import Literal

from langchain_core.tools import tool

from eyes import playing
from hands import reasons
from hands.browser import showing

PLAY = "play"
PAUSE = "pause"

# THE WAKE LOCK IS DROPPED A MOMENT AFTER THE KEY LANDS, NOT THE INSTANT IT DOES.
SETTLE_SECONDS = 1.2


@tool
def bring_to_front(what: str) -> str:
    """Bring a page that is already open in a browser to the front, filling the
    screen so the person can see it. Give a few words from its title or address,
    for example "Game of Thrones" or "hotstar".

    This is how you finish what already_open found with "show": it switches to
    that tab, raises its window above everything else and makes it full size. It
    does not start or stop anything — to do that, use play_pause afterwards.

    This moves what is in front of them, so only call it when they asked for the
    thing itself. Someone asking which show it is, or how far through it they
    are, wants an answer, not their work covered over.

    If this says no such tab is open, then it is not open, and you should search
    for it and open it instead."""
    if not what.strip():
        return reasons.no("Say which page to bring to the front.")

    found = showing.shown(what)

    if found is None:
        return reasons.no(
            f"No open tab matches {what}, so nothing was brought to the front. "
            f"It is not already open: search for it and open it instead."
        )

    browser, title = found

    return f'"{title}" is in front of them now, in {browser}, filling the screen.'


@tool
def play_pause(want: Literal[PLAY, PAUSE]) -> str:
    """Start or stop whatever is playing in the front window. Say "play" to
    resume, put back on, carry on with or continue something, and "pause" to
    stop, pause or hold it.

    Use this after bring_to_front. It checks what the player is actually doing
    first, so asking to play something already playing leaves it alone rather
    than stopping it, and it checks again afterwards and tells you what is true
    now. Believe that answer: it is the only thing here that knows, because a
    streaming site blanks its picture and the video is black on screen even
    while it plays.

    If it says it could not tell, say what you pressed rather than claiming the
    show is playing."""
    was = playing.playing()

    if was is not None and was == (want == PLAY):
        return f"It is already {'playing' if was else 'paused'}, so nothing was pressed."

    if not showing.played():
        return reasons.no("The play key would not go through, so nothing changed.")

    time.sleep(SETTLE_SECONDS)
    now = playing.playing()

    if now is None:
        return f"Pressed play and pause. I cannot tell which way it went, so say only that."

    if now == (want == PLAY):
        return f"It is {'playing' if now else 'paused'} now."

    return reasons.no(
        f"I pressed it but it is still {'playing' if now else 'paused'}. "
        f"Something else has the keyboard, so nothing was {want}ed."
    )


TOOLS = [bring_to_front, play_pause]
