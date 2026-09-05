"""THE TOOLS."""

from langchain_core.tools import tool

import eyes
from hands import reasons
from hands.desktop import acting, attaching


def went(done):
    """WHAT HAPPENED, MARKED AS A NO WHEN IT DID NOT HAPPEN."""
    return done.said if done.worked else reasons.no(done.said)


@tool
def list_controls() -> str:
    """List the buttons, text fields, checkboxes and menus in the window that is
    in front, with what each one says and whether it is greyed out or ticked.

    Use this before clicking when you are not certain what is on the screen, and
    use it to check the result of something you just did. It is fast and it is
    the most reliable way to know what can be clicked, because the application
    is asked directly rather than guessed at from a picture.

    This is different from screen with "read", which reads the words off it as
    a picture. Prefer this one when you want to know what you can press."""
    model = eyes.current()
    model.refresh()

    return model.summary()


@tool
def control_app(action: str, target: str = "", text: str = "", keys: str = "",
                path: str = "", amount: int = 1, double: bool = False,
                right: bool = False) -> str:
    """Work the window in front by hand: click it, type into it, press a key,
    attach a file or scroll it. Do this only for things that have no proper
    tool — open_app starts an application, open_url opens an address, and
    system_control works the volume, brightness and Wi-Fi, all faster and safer
    than clicking around.

    action:
    "click" with target, named the way a person would name it: "Send", "the
    search box", "Documents in the sidebar". Never coordinates. double for a
    double click, right for a context menu.
    "type" with text, and optionally target as a field to click first. For a
    single key or a shortcut use "press" instead.
    "press" with keys, one key or one shortcut written with plus signs:
    "enter", "esc", "cmd+s", "cmd+shift+t". On macOS the command key is "cmd";
    on Windows use "ctrl".
    "attach" with path, and optionally target as the box it belongs in. For a
    resume, a photo, anything to send someone. Use this rather than hunting for
    a paperclip. Open the right chat, mail or page first. It attaches only —
    nothing is sent until you press Enter or click Send.
    "scroll" with target as "up", "down", "left" or "right", and amount as how
    many steps. Scroll a step, then list_controls to see if it appeared.

    The screen is read again on every call and checked afterwards to confirm
    something actually happened, so believe the answer rather than assuming it
    worked. Anything that deletes, sends, buys or installs is shown to the user
    for approval first."""
    wanted = (action or "").strip().lower()

    if wanted == "click":
        return went(acting.clicked(
            target, times=2 if double else 1, button="right" if right else "left"
        ))

    if wanted == "type":
        return went(acting.typed(text, target))

    if wanted == "press":
        return went(acting.pressed(keys))

    if wanted == "attach":
        return went(attaching.attached(path, target))

    if wanted == "scroll":
        return went(acting.scrolled(target, amount))

    return reasons.no(f"I can click, type, press, attach or scroll, not {action}.")


TOOLS = [list_controls, control_app]
