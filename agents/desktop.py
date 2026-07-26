"""
WORKING THE DESKTOP: THE POINTER AND THE KEYBOARD.

THE OTHER HALF OF SEEING. vision.py SAYS WHERE SOMETHING IS AND THIS PUTS THE
POINTER THERE, WHICH IS WHY NOTHING HERE TAKES A COORDINATE: A MODEL THAT CAN
NAME A PLACE IN PIXELS CAN NAME THE WRONG ONE, AND A CLICK AT THE WRONG PLACE IS
NOT A WRONG ANSWER, IT IS A THING THAT HAPPENED. TOOLS TAKE A DESCRIPTION, THE
SCREEN IS READ FRESH, AND THE POINTER GOES WHERE THE WORDS ACTUALLY ARE.

ONE ACT PER CALL, AND THE SCREEN IS NEVER ASSUMED TO HAVE STAYED STILL BETWEEN
TWO OF THEM. THE MODEL LOOKS, DOES ONE THING, AND LOOKS AGAIN, BECAUSE A MENU
THAT OPENED HALF A SECOND LATE MAKES EVERY REMEMBERED POSITION A LIE.

LIKE THE SHELL, THIS HOLDS A KNIFE, AND THE GUARD IS THE SAME SHAPE: A LIST OF
WORDS THAT MEAN SOMETHING IS ABOUT TO BE SENT, SPENT OR DELETED, CHECKED AGAINST
WHAT IS WRITTEN ON THE THING BEING CLICKED. IT CATCHES A CARELESS MODEL, NOT A
HOSTILE ONE.

MACOS WANTS ACCESSIBILITY PERMISSION BEFORE ANY OF THIS WORKS. PUSH TO TALK
ALREADY ASKED FOR IT, SO IT IS USUALLY ALREADY GIVEN.
"""

import re
import sys
import time

from langchain_core.tools import tool
from pynput import keyboard, mouse

from agents import vision

WINDOWS = "win32"

# LONG ENOUGH FOR THE WINDOW UNDER THE POINTER TO NOTICE IT ARRIVED. WITHOUT IT
# THE FIRST CLICK OF A DRAG OR A MENU IS SOMETIMES EATEN.
SETTLE_SECONDS = 0.08

# HOW FAR ONE SCROLL GOES. THREE NOTCHES IS ABOUT A THIRD OF A WINDOW.
SCROLL_STEPS = 3

UP, DOWN, LEFT, RIGHT = "up", "down", "left", "right"

DIRECTIONS = {
    UP: (0, 1),
    DOWN: (0, -1),
    LEFT: (-1, 0),
    RIGHT: (1, 0),
}

# WHAT A PERSON CALLS A KEY, AND WHAT pynput CALLS IT. THE NAMES ON THE LEFT ARE
# THE ONES A MODEL WILL REACH FOR WITHOUT BEING TOLD.
KEYS = {
    "enter": keyboard.Key.enter, "return": keyboard.Key.enter,
    "tab": keyboard.Key.tab, "escape": keyboard.Key.esc, "esc": keyboard.Key.esc,
    "space": keyboard.Key.space, "backspace": keyboard.Key.backspace,
    "delete": keyboard.Key.delete, "up": keyboard.Key.up, "down": keyboard.Key.down,
    "left": keyboard.Key.left, "right": keyboard.Key.right,
    "home": keyboard.Key.home, "end": keyboard.Key.end,
    "pageup": keyboard.Key.page_up, "pagedown": keyboard.Key.page_down,
    "shift": keyboard.Key.shift, "alt": keyboard.Key.alt, "option": keyboard.Key.alt,
    "ctrl": keyboard.Key.ctrl, "control": keyboard.Key.ctrl,
}

# THE COMMAND KEY DOES NOT EXIST ON WINDOWS AND CONTROL DOES ITS JOB THERE, SO
# "cmd+c" MEANS COPY ON BOTH AND THE MODEL NEED NOT ASK WHICH MACHINE IT IS ON.
COMMAND = {"cmd", "command", "win", "super", "meta"}

# SHAPES THAT GO PAST A PERSON FIRST, WITH HOW TO SAY WHY OUT LOUD. MATCHED
# AGAINST WHAT IS WRITTEN ON THE THING BEING CLICKED.
RISKY = [
    (r"\b(delete|remove|erase|trash|bin|discard|clear all)\b", "deletes something"),
    (r"\b(send|post|publish|reply all|share)\b", "sends something to other people"),
    (r"\b(buy|pay|purchase|order|checkout|subscribe|donate)\b", "spends money"),
    (r"\b(install|uninstall|update now|upgrade)\b", "installs or removes software"),
    (r"\b(allow|grant|trust|always allow)\b", "grants a permission"),
    (r"\b(shut down|restart|log ?out|sign ?out|quit)\b", "ends the session"),
    (r"\b(format|erase disk|reset|factory)\b", "erases or resets something"),
]

CHECKS = [(re.compile(pattern, re.IGNORECASE), reason) for pattern, reason in RISKY]

# THE SAME FOR KEYS. PLAIN DELETE IS ORDINARY TYPING, DELETE WITH A MODIFIER IS
# A FILE GOING TO THE BIN.
RISKY_KEYS = [
    (lambda keys: "delete" in keys and len(keys) > 1, "deletes something"),
    (lambda keys: "backspace" in keys and len(keys) > 1, "deletes something"),
    (lambda keys: "q" in keys and len(keys) > 1, "quits an app, losing anything unsaved"),
    (lambda keys: "w" in keys and len(keys) > 1, "closes a window, losing anything unsaved"),
]

YES = {"y", "yes", "yeah", "yep", "ok", "okay", "sure", "go ahead", "do it"}

REFUSED = "Cancelled, the user said no. Do not try to do it another way."

pointer = mouse.Controller()
typist = keyboard.Controller()


def console_confirm(what, reason):
    """THE DEFAULT WAY OF ASKING. A SPOKEN ONE CAN REPLACE IT THROUGH asks()."""
    print(f"\n  Happy wants to do something that {reason}:\n    {what}")

    try:
        return input("  Allow it? [y/N] ").strip().lower() in YES
    except (EOFError, KeyboardInterrupt):
        print()
        return False


confirm = console_confirm


def asks(handler):
    """WIRE UP HOW HAPPY ASKS BEFORE DOING SOMETHING THAT CANNOT BE UNDONE.

    handler(what, reason) -> bool. PASSING None PUTS THE CONSOLE BACK.
    """
    global confirm

    confirm = handler or console_confirm


def danger(label):
    """WHY CLICKING THIS NEEDS ASKING ABOUT, OR None WHEN IT DOES NOT."""
    for check, reason in CHECKS:
        if check.search(label or ""):
            return reason

    return None


def key(name):
    """ONE KEY BY THE NAME A PERSON WOULD USE FOR IT."""
    called = name.strip().lower()

    if called in COMMAND:
        return keyboard.Key.ctrl if sys.platform == WINDOWS else keyboard.Key.cmd

    if called in KEYS:
        return KEYS[called]

    return called if len(called) == 1 else None


def combination(keys):
    """"cmd+shift+s" AS THE KEYS TO HOLD AND THE ONE TO TAP, OR None."""
    names = [part for part in re.split(r"[+\s]+", keys.strip()) if part]
    found = [key(name) for name in names]

    if not names or None in found:
        return None

    return found[:-1], found[-1]


def press(holding, tapped):
    """HOLD THE MODIFIERS, TAP THE KEY, LET GO IN THE OPPOSITE ORDER."""
    for held in holding:
        typist.press(held)

    try:
        typist.press(tapped)
        typist.release(tapped)
    finally:
        for held in reversed(holding):
            typist.release(held)


def put(x, y):
    """THE POINTER, THERE, WITH A MOMENT FOR THE WINDOW TO NOTICE."""
    pointer.position = (x, y)
    time.sleep(SETTLE_SECONDS)


# TOOLS. THE DESCRIPTIONS BELOW ARE READ BY THE MODEL, NOT BY US, SO THEY ARE
# WRITTEN AS PLAIN PROSE RATHER THAN AS COMMENTS.


@tool
def click_on(target: str, double: bool = False) -> str:
    """Click something on the screen. Describe what to click the way it is
    labelled or the way a person would say it: "Send", "the search box", "the
    File menu", "the red close button". Do not give coordinates, they are worked
    out here. Set double to true to double click, which is what opens a file or
    a folder from a list.

    The screen is read fresh on every call, so call this once per thing you want
    to click and read the screen again afterwards to see what happened. Anything
    that spends money, deletes, sends or grants permission is shown to the user
    for approval first."""
    try:
        found = vision.where(target)
    except vision.VisionError as problem:
        return str(problem)

    if found is None:
        return f"I cannot find {target} on the screen."

    reason = danger(found.label)

    if reason and not confirm(f"click {found.label!r}", reason):
        return REFUSED

    put(found.x, found.y)
    pointer.click(mouse.Button.left, 2 if double else 1)

    return f"Clicked {found.label!r} at {found.x}, {found.y} ({found.how})."


@tool
def type_text(text: str) -> str:
    """Type text wherever the cursor already is. This types, it does not click
    first, so click the box you want it to go in beforehand unless the cursor is
    already there. Use press_keys for keys that are not letters, like enter or
    escape."""
    if not text:
        return "Nothing to type."

    typist.type(text)

    return f"Typed {len(text)} characters."


@tool
def press_keys(keys: str) -> str:
    """Press a key or a combination of keys, like "enter", "escape", "tab",
    "cmd+s", "cmd+shift+4" or "ctrl+c". Use this to confirm a dialog, save,
    copy, paste, switch windows, or move around with the arrow keys. On Windows
    "cmd" is taken to mean control, so the same shortcut works on both."""
    parsed = combination(keys)

    if parsed is None:
        return f"I do not know the keys {keys}."

    holding, tapped = parsed
    named = [part.lower() for part in re.split(r"[+\s]+", keys.strip()) if part]

    for check, reason in RISKY_KEYS:
        if check(named) and not confirm(f"press {keys}", reason):
            return REFUSED

    press(holding, tapped)

    return f"Pressed {keys}."


@tool
def scroll(direction: str = DOWN, amount: int = SCROLL_STEPS, target: str = "") -> str:
    """Scroll the screen up, down, left or right. Amount is in notches of a
    mouse wheel, about a third of a window each. Optionally give a target to
    move the pointer over first, which is how you scroll one panel of a window
    rather than another."""
    way = DIRECTIONS.get(direction.strip().lower())

    if way is None:
        return f"I can scroll up, down, left or right, not {direction}."

    if target:
        try:
            found = vision.where(target)
        except vision.VisionError as problem:
            return str(problem)

        if found is None:
            return f"I cannot find {target} on the screen."

        put(found.x, found.y)

    across, along = way
    pointer.scroll(across * amount, along * amount)

    return f"Scrolled {direction} {amount}."


TOOLS = [click_on, type_text, press_keys, scroll]


if __name__ == "__main__":  # WHERE WOULD IT CLICK, WITHOUT CLICKING.
    wanted = " ".join(sys.argv[1:])

    if not wanted:
        sys.exit("Usage: python agents/desktop.py <something on the screen>")

    place = vision.where(wanted)

    print(f"{wanted!r} -> {place}" if place else f"{wanted!r} is not on the screen.")
