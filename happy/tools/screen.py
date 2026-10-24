"""Seeing what is on screen, and pressing, typing and clicking in the front app."""

import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Annotated

from happy.system import Failed, native
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
    for combo in keys.split(","):
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


PRESSABLE = {"AXButton", "AXLink", "AXMenuItem", "AXMenuBarItem", "AXCheckBox", "AXRadioButton", "AXTab",
             "AXPopUpButton", "AXCell", "AXRow", "AXStaticText", "AXImage", "AXTextField", "AXDisclosureTriangle"}


def ax(element, name):
    from ApplicationServices import AXUIElementCopyAttributeValue

    err, value = AXUIElementCopyAttributeValue(element, name, None)
    return None if err else value


def candidates(root, words, budget=4000):
    """Elements in the front window whose name contains the words, nearest the top first."""
    found, queue, seen = [], [(root, 0)], 0
    while queue and seen < budget:
        element, depth = queue.pop(0)
        seen += 1
        role = ax(element, "AXRole") or ""
        label = " ".join(str(ax(element, k) or "") for k in ("AXTitle", "AXDescription", "AXValue", "AXHelp"))
        if role in PRESSABLE and words in label.lower():
            found.append((role, label.strip(), element, depth))
        for child in ax(element, "AXChildren") or []:
            queue.append((child, depth + 1))
    rank = {"AXButton": 0, "AXLink": 0, "AXMenuItem": 1, "AXTab": 1, "AXCheckBox": 1, "AXRadioButton": 1}
    return sorted(found, key=lambda f: (rank.get(f[0], 2), len(f[1]), f[3]))


def click_at(element):
    from Quartz import (CGEventCreateMouseEvent, CGEventPost, kCGEventLeftMouseDown, kCGEventLeftMouseUp,
                        kCGHIDEventTap, kCGMouseButtonLeft)
    from ApplicationServices import AXValueGetValue, kAXValueCGPointType, kAXValueCGSizeType

    _, point = AXValueGetValue(ax(element, "AXPosition"), kAXValueCGPointType, None)
    _, size = AXValueGetValue(ax(element, "AXSize"), kAXValueCGSizeType, None)
    centre = (point.x + size.width / 2, point.y + size.height / 2)
    for kind in (kCGEventLeftMouseDown, kCGEventLeftMouseUp):
        CGEventPost(kCGHIDEventTap, CGEventCreateMouseEvent(None, kind, centre, kCGMouseButtonLeft))
        time.sleep(0.03)


@tool(label="Clicking {target}")
def click(target: Annotated[str, "the words on the button, link or item to click"]):
    """Click a button, link, tab or menu item in the front app by the words on it."""
    if sys.platform != "darwin":
        return "Clicking by name needs a Mac for now."
    from AppKit import NSWorkspace
    from ApplicationServices import AXUIElementCreateApplication, AXUIElementPerformAction, AXUIElementSetAttributeValue

    if not native.trusted():
        return "Happy needs Accessibility permission to click: System Settings, Privacy & Security, Accessibility."
    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    root = AXUIElementCreateApplication(app.processIdentifier())
    AXUIElementSetAttributeValue(root, "AXManualAccessibility", True)
    window = ax(root, "AXFocusedWindow") or root
    hits = candidates(window, target.lower().strip())
    if not hits:
        return f"Could not find anything labelled {target} in {app.localizedName()}."
    role, label, element, _ = hits[0]
    if AXUIElementPerformAction(element, "AXPress") != 0:
        click_at(element)
    return f"Clicked {label[:80]} ({role.removeprefix('AX').lower()})."
