"""THE TOOLS."""

from langchain_core.tools import tool

import eyes
from hands import asking
from hands.desktop import acting, attaching


def went(done):
    """WHAT HAPPENED, MARKED AS A NO WHEN IT DID NOT HAPPEN."""
    return done.said if done.worked else asking.no(done.said)


@tool
def list_controls() -> str:
    """List the buttons, text fields, checkboxes and menus in the window that is
    in front, with what each one says and whether it is greyed out or ticked.

    Use this before clicking when you are not certain what is on the screen, and
    use it to check the result of something you just did. It is fast and it is
    the most reliable way to know what can be clicked, because the application
    is asked directly rather than guessed at from a picture.

    This is different from read_screen, which reads the words off the screen as
    a picture. Prefer this one when you want to know what you can press."""
    model = eyes.current()
    model.refresh()

    return model.summary()


@tool
def click_on(target: str, double: bool = False, right: bool = False) -> str:
    """Click something on the screen, named the way a person would name it, for
    example "Send", "the search box", "Documents in the sidebar". Never give
    coordinates. Set double for a double click, for example to open a file, and
    right for a right click to get a context menu.

    The screen is read again on every call, the thing is found by what it says,
    and afterwards the screen is checked to confirm something actually happened.
    You get told plainly when it did not, so believe the answer rather than
    assuming the click worked.

    Do this only for things that have no proper tool. To start an application
    use open_app, to open a web address use open_url, and to change the volume,
    brightness or Wi-Fi use the controls, all of which are faster and safer than
    clicking around. Anything whose label suggests it deletes, sends, buys or
    installs is shown to the user for approval first."""
    return went(acting.clicked(target, times=2 if double else 1, button="right" if right else "left"))


@tool
def type_text(text: str, into: str = "") -> str:
    """Type text on the keyboard, into whatever currently has the cursor.
    Optionally give into as the name of a field to click first, for example
    into="the search box".

    Afterwards the screen is checked to confirm the text actually arrived, and
    you are told if it did not. Use this for filling in a form, writing a
    message or searching inside an application. To press a shortcut or a single
    key like Enter, use press_keys instead."""
    return went(acting.typed(text, into))


@tool
def press_keys(keys: str) -> str:
    """Press one key or one keyboard shortcut, written with plus signs, for
    example "enter", "esc", "tab", "cmd+s", "cmd+shift+t", "ctrl+c".

    Use this for confirming a dialog, saving, copying, closing a tab, or moving
    around with the arrow keys. On macOS the command key is "cmd" and on Windows
    use "ctrl". Shortcuts that quit an application or delete something are shown
    to the user for approval first."""
    return went(acting.pressed(keys))


@tool
def attach_file(path: str, into: str = "") -> str:
    """Attach a file to a message, an email or an upload box: a resume, a photo,
    a document, anything someone asks you to send or share with a person. Give
    the file as a full path or just a name like "resume", and optionally give
    into as the box it belongs in, for example into="the message box".

    Use this rather than looking for a paperclip or an attach button. Those
    icons often have no name for you to click, and this does what pressing one
    ends up doing: it puts the file itself on the clipboard and pastes it where
    the cursor is. It works anywhere a file can be dropped.

    Open the right chat, mail or page first, so the file lands in the right
    place. Afterwards the screen is checked for the file's name and you are told
    if it did not arrive. This attaches only. Nothing is sent until you press
    Enter or click Send, which you should do once you are told the file is
    there."""
    return went(attaching.attached(path, into))


@tool
def scroll(direction: str, amount: int = 1) -> str:
    """Scroll whatever is under the pointer. Direction is "up", "down", "left"
    or "right", and amount is how many steps, defaulting to one.

    Use this to bring something into view that is not on the screen yet. If you
    are looking for something in particular, scroll a step and then use
    list_controls or read_screen to see whether it has appeared."""
    return went(acting.scrolled(direction, amount))


TOOLS = [list_controls, click_on, type_text, attach_file, press_keys, scroll]
