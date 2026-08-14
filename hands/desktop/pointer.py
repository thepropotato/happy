"""THE POINTER AND THE KEYBOARD."""

import time

from hands.desktop import noticing

# WITHOUT A MOMENT BEFORE THE BUTTON GOES DOWN, SOME CONTROLS NEVER SEE THE CLICK.
HOVER_SECONDS = 0.06

# HOW LONG A KEY IS HELD. INSTANT PRESSES GET DROPPED BY SOME APPLICATIONS.
HOLD_SECONDS = 0.02

NOTCHES = 3

NAMES = {
    "cmd": "cmd",
    "command": "cmd",
    "win": "cmd",
    "super": "cmd",
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "option": "alt",
    "opt": "alt",
    "shift": "shift",
    "enter": "enter",
    "return": "enter",
    "tab": "tab",
    "esc": "esc",
    "escape": "esc",
    "space": "space",
    "backspace": "backspace",
    "delete": "delete",
    "del": "delete",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "home": "home",
    "end": "end",
    "pageup": "page_up",
    "pagedown": "page_down",
}

DIRECTIONS = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}


def mouse():
    from pynput.mouse import Controller

    return Controller()


def keyboard():
    from pynput.keyboard import Controller

    return Controller()


def key(name):
    """ONE KEY, AS pynput WANTS IT. A PLAIN LETTER STAYS A LETTER."""
    from pynput.keyboard import Key

    wanted = NAMES.get(name.strip().lower(), name.strip().lower())

    if len(wanted) == 1:
        return wanted

    return getattr(Key, wanted, None)


def at(x, y):
    """PUT THE POINTER SOMEWHERE AND LEAVE IT THERE."""
    noticing.watch().ours()
    mouse().position = (int(x), int(y))


def click(x, y, times=1, button="left"):
    """PRESS SOMEWHERE."""
    from pynput.mouse import Button

    which = Button.right if button == "right" else Button.left
    hand = mouse()

    noticing.watch().ours()
    hand.position = (int(x), int(y))
    time.sleep(HOVER_SECONDS)

    noticing.watch().ours()
    hand.click(which, times)


def write(text):
    """TYPE SOMETHING WHEREVER THE KEYBOARD CURRENTLY IS."""
    noticing.watch().ours(len(text) * 0.01 + 1.0)
    keyboard().type(text)


def parts(keys):
    return [part for part in str(keys).replace(" ", "").split("+") if part]


def unknown_keys(keys):
    """WHY THIS SHORTCUT CANNOT BE PRESSED, OR None."""
    wanted = parts(keys)

    if not wanted:
        return "There were no keys to press."

    missing = [part for part in wanted if key(part) is None]

    return f"I do not know the key {' or '.join(missing)}." if missing else None


def unknown_direction(direction):
    """WHY THIS IS NOT A DIRECTION, OR None."""
    if str(direction).strip().lower() in DIRECTIONS:
        return None

    return f"I can scroll up, down, left or right, not {direction}."


def press(keys):
    """ONE SHORTCUT, LIKE "cmd+s" OR "enter". RETURNS THE COMPLAINT, OR None."""
    complaint = unknown_keys(keys)

    if complaint:
        return complaint

    pressed = [key(part) for part in parts(keys)]
    hand = keyboard()
    noticing.watch().ours()

    # THE LAST ONE IS THE KEY, EVERYTHING BEFORE IT IS HELD DOWN FOR IT.
    holding, final = pressed[:-1], pressed[-1]

    for each in holding:
        hand.press(each)

    try:
        hand.press(final)
        time.sleep(HOLD_SECONDS)
        hand.release(final)
    finally:  # A MODIFIER LEFT DOWN WOULD BREAK EVERY KEYSTROKE AFTER THIS ONE.
        for each in reversed(holding):
            hand.release(each)

    return None


def scroll(direction, amount=1):
    """SCROLL THE THING UNDER THE POINTER. RETURNS THE COMPLAINT, OR None."""
    complaint = unknown_direction(direction)

    if complaint:
        return complaint

    across, along = DIRECTIONS[str(direction).strip().lower()]
    turns = max(1, int(amount)) * NOTCHES

    noticing.watch().ours(turns * 0.02 + 0.5)
    mouse().scroll(across * turns, along * turns)

    return None


def where():
    """WHERE THE POINTER IS NOW."""
    x, y = mouse().position

    return int(x), int(y)
