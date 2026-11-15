"""Seeing what is on screen, and pressing, typing and clicking in the front app."""

import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Annotated, Literal

from happy.system import Failed, native
from happy import tools
from happy.tools import Image, tool


def shrink(png, longest=1440):
    """Scales a Retina screenshot down so it costs fewer tokens to look at."""
    if sys.platform != "darwin":
        return png
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "shot.png"
        path.write_bytes(png)
        subprocess.run(["sips", "-Z", str(longest), str(path)], capture_output=True)
        return path.read_bytes()


def describe():
    from happy.tools import browser

    lines = [f"Front app: {native.frontmost() or 'unknown'}"]
    title = native.front_window_title()
    if title:
        lines.append(f"Window: {title}")
    if sys.platform == "darwin":
        app = browser.front_browser()
        if app:
            try:
                tab = browser.current(browser.list_tabs(app))
                if tab:
                    lines.append(f"{app} tab in front: {tab['title']} — {tab['url']}")
            except Failed:
                pass
    try:
        chosen = native.selected_text()
        if chosen:
            lines.append(f"Selected text: {chosen[:2000]}")
    except Exception:
        pass
    return "\n".join(lines)


@tool(label="Looking at the screen")
def look_at_screen():
    """See what is on the screen right now: the app and window in front, the browser tab, any selected text, and a picture when the brain can see."""
    note = describe()
    try:
        return Image(shrink(native.screenshot()), note)
    except Failed:
        return note


@tool(label="Pressing {keys}")
def press_keys(keys: Annotated[str, "like cmd+t, ctrl+shift+tab, escape or return"]):
    """Press a key or shortcut the person asked for in the app in front. Never use it to run commands or do coding work."""
    for combo in re.split(r",\s+|\s+then\s+", keys.strip()):
        native.press(combo.strip())
        time.sleep(0.05)
    return f"Pressed {keys}."


@tool(label="Typing")
def type_text(text: Annotated[str, "exactly what to type"], then_enter: bool = False):
    """Type text the person dictated into the field they have focused. Never use it to run commands, write code or work in a terminal."""
    native.paste(text)
    if then_enter:
        native.press("return")
    return "Typed it."


# THE LAST LISTING, SO "CLICK 4" MEANS THE FOURTH THING look SHOWED IN THAT SAME APP.
listing = {"pid": None, "items": []}


def all_controls(win):
    controls = win.via
    found = controls.controls(win)
    if len(found) < 3:
        # CHROME AND ELECTRON APPS BUILD THEIR TREE A MOMENT AFTER BEING ASKED FOR IT.
        time.sleep(0.8)
        found = controls.controls(win)
    return found


def words_of(text):
    return [w for w in re.split(r"[^\w']+", text.lower()) if w]


# WORDS THAT SAY WHAT KIND OF CONTROL IT IS, NOT WHICH ONE: "THE SEND BUTTON" IS THE BUTTON CALLED SEND.
KIND_WORDS = {"the", "a", "an", "button", "link", "tab", "box", "field", "checkbox", "check", "icon", "option", "item", "menu",
              "dropdown", "toggle", "switch", "control", "text", "input", "on", "this", "page", "window"}


def ranked(found, target, fields=False):
    """The controls the words could mean, best first: the whole name, then its start, then every word in it."""
    hits = matches(found, words_of(target), fields)
    bare = [w for w in words_of(target) if w not in KIND_WORDS]
    return hits or (matches(found, bare, fields) if bare else [])


def matches(found, words, fields):
    wanted = " ".join(words)
    scored = []
    for control in found:
        name = " ".join(words_of(control.label))
        if not name:
            continue
        fit = 0 if name == wanted else 1 if name.startswith(wanted) else 2 if wanted in name else \
            3 if all(w in name.split() for w in wanted.split()) else None
        if fit is None:
            continue
        kind = 0 if (control.field if fields else control.listed) else 1
        scored.append((fit, kind, not control.enabled, len(name), control))
    return [s[-1] for s in sorted(scored, key=lambda s: s[:4])]


def pick(win, target, fields=False, found=None):
    """The control a target names, by the number look gave it or by its words."""
    from happy.system import Failed

    number = target.strip().lstrip("#")
    if number.isdigit():
        if listing["pid"] != win.pid or not 0 < int(number) <= len(listing["items"]):
            raise Failed(f"There is no number {number} from a look at {win.app}. Look at it first, or name the control by its words.")
        return listing["items"][int(number) - 1]
    found = found if found is not None else all_controls(win)
    if not found:
        raise Failed(f"{win.app} does not show its controls to other apps, so nothing in it can be named. "
                     "Keyboard shortcuts or a look at the screen are the way in.")
    hits = ranked(found, target, fields)
    if not hits:
        kinds = "fields" if fields else "controls"
        near = ", ".join(c.label[:40] for c in found if (c.field if fields else c.listed))[:500]
        raise Failed(f"Nothing called {target} in {win.app}. Its {kinds} include: {near or 'none with names'}.")
    return hits[0]


def state(win, found=None):
    controls = win.via
    return controls.title(win), [(c.label, c.value) for c in (found if found is not None else controls.controls(win))]


def change(before, after, control, window):
    """What visibly changed after an action, in words, or None."""
    controls = window.via
    if not controls.alive(window):
        return "The window closed."
    if after[0] != before[0]:
        return f"The window is now {after[0] or 'untitled'}."
    if not controls.alive(control) or len(after[1]) != len(before[1]):
        return "The window changed."
    if after[1] != before[1]:
        return "Something in the window changed."
    return None


def look(win):
    found = all_controls(win)
    items = [c for c in found if c.listed]
    listing.update(pid=win.pid, items=items)
    if not items:
        return (f"{win.app} does not show its controls to other apps, so nothing in it can be named. "
                "Keyboard shortcuts or a look at the screen are the way in.")
    lines = []
    for n, c in enumerate(items[:80], 1):
        held = f": {c.value[:60]!r}" if c.field and c.value and c.value != c.label else ""
        lines.append(f"{n}. {c.kind} {c.label[:70]}{held}{'' if c.enabled else ' (greyed out)'}")
    more = f"\n…and {len(items) - 80} more; name one by its words." if len(items) > 80 else ""
    return (f"{win.app}, window {win.title or 'untitled'}{'' if win.front else ' (behind other windows)'}. "
            f"Its controls, top to bottom; a number here clicks or types into that one:\n" + "\n".join(lines) + more)


def labelled(args):
    action, target, app = args.get("action", ""), args.get("target", ""), args.get("app", "")
    where = f" in {app}" if app else ""
    return {"look": f"Looking at the controls{where}", "click": f"Clicking {target}{where}",
            "type": f"Typing into {target}{where}", "menu": f"Choosing {target}{where}",
            "scroll": f"Scrolling {target or 'down'}{where}"}.get(action, "Using the app")


@tool(label=labelled)
def use_app(
    action: Literal["look", "click", "type", "menu", "scroll"],
    target: Annotated[str, "the words on the control, its number from look, a menu path like View > as List, or top, bottom, up or down"] = "",
    text: str = "",
    app: str = "",
    then_enter: bool = False,
):
    """Click, type into, pick a menu item or scroll inside an app by the words on the control, even with the app behind; look lists its controls first."""
    from happy.system import Failed, controls, web_controls

    if controls is None:
        return "Working inside apps needs a Mac or Windows."
    if not native.trusted():
        return "Happy needs Accessibility permission for that: System Settings, Privacy & Security, Accessibility."
    try:
        # A PAGE IN THE PERSON'S CHROME GOES THROUGH agent-browser WHEN IT IS CONNECTED; MENUS STAY WITH THE OS.
        if action != "menu" and web_controls.usable(app or native.frontmost()):
            controls = web_controls
        win = controls.window(app)
        win.via = controls
        if action == "click" and re.search(r"\S\s*(?:>|→)\s*\S", target):
            # "VIEW > AS LIST" IS A MENU PATH, WHATEVER THE ACTION SAID.
            action = "menu"
        if action == "look":
            return look(win)
        if action == "menu":
            path = [p.strip() for p in re.split(r"\s*(?:>|→|/|,)\s*", target) if p.strip()]
            if not path:
                return "Say which menu item, like File > Export."
            # AN APP GREYS OUT ITS MENUS WHILE IT IS NOT THE ONE IN FRONT.
            controls.bring_forward(win)
            walked = controls.menu(win, path)
            return f"Chose {' > '.join(walked)} in {win.app}."
        if action == "scroll":
            where = next((w for w in ("top", "bottom", "up", "down") if w in target.lower()), "down")
            said = " ".join(words_of(tools.asked.get() or ""))
            # "SCROLL TO THE BOTTOM" SENT AS "DOWN" WOULD MOVE A QUARTER AND BE CALLED THE BOTTOM.
            if where == "down" and re.search(r"\b(bottom|end)\b", said):
                where = "bottom"
            elif where == "up" and re.search(r"\b(top|beginning|start)\b", said):
                where = "top"
            spot = controls.scroll(win, where)
            at = "" if spot is None else " It is at the top." if spot <= 0.01 else " It is at the bottom." if spot >= 0.99 else ""
            return f"Scrolled {where} in {win.app}.{at}"
        if not target.strip():
            return f"Say which {'field' if action == 'type' else 'control'} in {win.app}, by its words or its number from look."
        if action == "type":
            field = pick(win, target, fields=True)
            if not field.field:
                # A SEARCH BUTTON THAT OPENS INTO A FIELD, AS IN FINDER: PRESS IT, THEN THE FIELD IS THERE.
                controls.press(field, win)
                time.sleep(0.4)
                opened = controls.focused_field(win)
                if opened is None:
                    return f"{field.label} in {win.app} is a {field.kind}, not somewhere to type, and pressing it opened no field."
                field = opened
            if not controls.set_text(field, text, win):
                return f"Typed into {field.label} in {win.app}, but it does not show the text back, so it could not be checked."
            if then_enter:
                if hasattr(controls, "enter"):
                    controls.enter(win)
                else:
                    controls.bring_forward(win)
                    native.press("return")
            return f"{field.label} in {win.app} now says {text[:200]!r}{' and Return was pressed' if then_enter else ''}."
        found = all_controls(win)
        control = pick(win, target, found=found)
        if not control.enabled:
            return f"The {control.kind} {control.label} in {win.app} is greyed out, so it cannot be pressed right now."
        before = state(win, found)
        how = controls.press(control, win)
        time.sleep(0.4)
        seen = change(before, state(win), control, win)
        done = f"{how.capitalize()} the {control.kind} {control.label[:80]} in {win.app}."
        return f"{done} {seen}" if seen else f"{done} Nothing in the window changed that could be seen, so check before saying it worked."
    except Failed as error:
        return str(error)
