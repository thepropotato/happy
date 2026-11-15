"""Reading and working the controls inside any Mac app through the Accessibility API, without needing it in front."""

import time
from dataclasses import dataclass

from happy.system.macos import Failed

FIELDS = {"AXTextField", "AXTextArea", "AXSearchField", "AXComboBox", "AXSecureTextField"}
PRESSABLE = {"AXButton", "AXLink", "AXMenuItem", "AXMenuButton", "AXCheckBox", "AXRadioButton", "AXTab", "AXPopUpButton",
             "AXCell", "AXRow", "AXDisclosureTriangle", "AXIncrementor", "AXSlider", "AXImage", "AXStaticText"} | FIELDS
# ROLES WORTH LISTING ON THEIR OWN; TEXT AND PICTURES ARE ONLY PRESSED WHEN NAMED, BECAUSE A WINDOW HOLDS HUNDREDS.
LISTED = PRESSABLE - {"AXStaticText", "AXImage", "AXCell", "AXRow"}
ASKED = ["AXRole", "AXSubrole", "AXTitle", "AXDescription", "AXValue", "AXPlaceholderValue", "AXHelp", "AXEnabled",
         "AXChildren", "AXPosition", "AXSize"]
KINDS = {"AXButton": "button", "AXLink": "link", "AXMenuItem": "menu item", "AXMenuButton": "menu button", "AXCheckBox": "checkbox",
         "AXRadioButton": "option", "AXTab": "tab", "AXPopUpButton": "pop-up menu", "AXCell": "cell", "AXRow": "row",
         "AXDisclosureTriangle": "disclosure", "AXIncrementor": "stepper", "AXSlider": "slider", "AXImage": "image",
         "AXStaticText": "text", "AXTextField": "text field", "AXTextArea": "text area", "AXSearchField": "search field",
         "AXComboBox": "combo box", "AXSecureTextField": "password field"}


@dataclass
class Control:
    role: str
    label: str
    value: str
    enabled: bool
    frame: tuple | None
    element: object
    depth: int

    @property
    def kind(self):
        return KINDS.get(self.role, self.role.removeprefix("AX").lower())

    @property
    def field(self):
        return self.role in FIELDS

    @property
    def listed(self):
        return self.role in LISTED


@dataclass
class Window:
    app: str
    title: str
    pid: int
    root: object
    element: object
    front: bool


def plain(value):
    """An attribute as Python, with the API's error placeholders turned into None."""
    from ApplicationServices import AXValueGetType, kAXValueAXErrorType

    if value is None:
        return None
    if type(value).__name__.startswith("AXValue"):
        return None if AXValueGetType(value) == kAXValueAXErrorType else value
    return value


def attr(element, name):
    from ApplicationServices import AXUIElementCopyAttributeValue

    err, value = AXUIElementCopyAttributeValue(element, name, None)
    return None if err else plain(value)


def attrs(element, names):
    from ApplicationServices import AXUIElementCopyMultipleAttributeValues

    err, values = AXUIElementCopyMultipleAttributeValues(element, names, 0, None)
    if err or values is None:
        return dict.fromkeys(names)
    return {name: plain(value) for name, value in zip(names, values)}


def frame(position, size):
    from ApplicationServices import AXValueGetValue, kAXValueCGPointType, kAXValueCGSizeType

    if position is None or size is None:
        return None
    _, point = AXValueGetValue(position, kAXValueCGPointType, None)
    _, extent = AXValueGetValue(size, kAXValueCGSizeType, None)
    return (point.x, point.y, extent.width, extent.height)


def running(name):
    """The running app whose name matches what was said, best match first."""
    from AppKit import NSWorkspace

    wanted = name.lower().strip()
    apps = [a for a in NSWorkspace.sharedWorkspace().runningApplications() if a.activationPolicy() == 0 and a.localizedName()]
    for test in (lambda n: n == wanted, lambda n: n.startswith(wanted), lambda n: wanted in n,
                 lambda n: any(word in n.split() for word in wanted.split())):
        hits = [a for a in apps if test(a.localizedName().lower())]
        if hits:
            return hits[0]
    return None


def window(app=""):
    """The window to work in: the named app's, or the app in front."""
    import os

    from AppKit import NSWorkspace
    from ApplicationServices import AXUIElementCreateApplication, AXUIElementSetAttributeValue

    front = NSWorkspace.sharedWorkspace().frontmostApplication()
    target = running(app) if app else front
    if target is None:
        raise Failed(f"{app} is not open.")
    if target.processIdentifier() == os.getpid():
        raise Failed("Happy's own panel is in front, so there is nothing of theirs to work in. Name the app.")
    root = AXUIElementCreateApplication(target.processIdentifier())
    # CHROME AND ELECTRON APPS BUILD THEIR TREE ONLY WHEN ASKED; THIS IS THE ASKING.
    AXUIElementSetAttributeValue(root, "AXManualAccessibility", True)
    AXUIElementSetAttributeValue(root, "AXEnhancedUserInterface", True)
    element = attr(root, "AXFocusedWindow") or attr(root, "AXMainWindow") or next(iter(attr(root, "AXWindows") or []), None)
    if element is None:
        raise Failed(f"{target.localizedName()} has no window open.")
    return Window(target.localizedName(), attr(element, "AXTitle") or "", target.processIdentifier(), root, element,
                  bool(front) and front.processIdentifier() == target.processIdentifier())


def controls(win, roles=PRESSABLE, budget=6000):
    """Every control in the window with something to call it by, top to bottom, left to right."""
    found, queue, walked = [], [(win.element, 0)], 0
    while queue and walked < budget:
        element, depth = queue.pop(0)
        walked += 1
        a = attrs(element, ASKED)
        role = a["AXRole"] or ""
        value = a["AXValue"] if isinstance(a["AXValue"], str) else ""
        label = next((str(a[k]).strip() for k in ("AXTitle", "AXDescription", "AXPlaceholderValue", "AXHelp") if a[k] and str(a[k]).strip()), "")
        if role in FIELDS and not label:
            # AN UNNAMED SEARCH BOX STILL ANSWERS TO "SEARCH".
            label = labelled_by(element) or KINDS[role]
        if role in roles and (label or value):
            found.append(Control(role, label or value[:80], value, a["AXEnabled"] is not False, frame(a["AXPosition"], a["AXSize"]),
                                 element, depth))
        queue.extend((child, depth + 1) for child in a["AXChildren"] or [])
    found.sort(key=lambda c: (round(c.frame[1] / 8), c.frame[0]) if c.frame else (1e9, 0))
    # CHROME HANDS OVER A TAB AND ITS INNER BUTTON AS TWO ELEMENTS WITH ONE NAME IN ONE PLACE; KEEP THE OUTER ONE.
    kept, places = [], set()
    for control in found:
        place = (control.role, control.label, tuple(round(v / 4) for v in control.frame) if control.frame else id(control))
        if place not in places:
            places.add(place)
            kept.append(control)
    return kept


def labelled_by(element):
    title = attr(element, "AXTitleUIElement")
    return str(attr(title, "AXValue") or "").strip() if title is not None else ""


def press(control, win):
    """Presses a control the way the app itself would, falling back to a real click."""
    from ApplicationServices import AXUIElementPerformAction, AXUIElementSetAttributeValue

    for action in ("AXPress", "AXConfirm", "AXPick", "AXOpen"):
        if AXUIElementPerformAction(control.element, action) == 0:
            return "pressed"
    if control.role in ("AXRow", "AXCell") and AXUIElementSetAttributeValue(control.element, "AXSelected", True) == 0:
        return "selected"
    if control.frame is None:
        raise Failed(f"The {control.kind} {control.label} could not be pressed.")
    # A REAL CLICK LANDS ON WHATEVER IS ON TOP, SO THE APP COMES FORWARD FIRST.
    bring_forward(win)
    mouse_click(control.frame)
    return "clicked"


def bring_forward(win):
    from AppKit import NSApplicationActivateIgnoringOtherApps, NSRunningApplication
    from ApplicationServices import AXUIElementPerformAction

    if not win.front:
        NSRunningApplication.runningApplicationWithProcessIdentifier_(win.pid).activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
        AXUIElementPerformAction(win.element, "AXRaise")
        time.sleep(0.3)
        win.front = True


def mouse_click(box):
    from Quartz import (CGEventCreateMouseEvent, CGEventPost, kCGEventLeftMouseDown, kCGEventLeftMouseUp,
                        kCGHIDEventTap, kCGMouseButtonLeft)

    centre = (box[0] + box[2] / 2, box[1] + box[3] / 2)
    for kind in (kCGEventLeftMouseDown, kCGEventLeftMouseUp):
        CGEventPost(kCGHIDEventTap, CGEventCreateMouseEvent(None, kind, centre, kCGMouseButtonLeft))
        time.sleep(0.03)


def set_text(control, text, win, add=False):
    """Puts text in a field and reads it back; True when the field holds it."""
    from ApplicationServices import AXUIElementSetAttributeValue

    wanted = (control.value + text) if add else text
    AXUIElementSetAttributeValue(control.element, "AXFocused", True)
    if AXUIElementSetAttributeValue(control.element, "AXValue", wanted) == 0:
        time.sleep(0.1)
        if (attr(control.element, "AXValue") or "") == wanted:
            return True
    # SOME FIELDS IGNORE A SET VALUE; TYPING INTO THEM NEEDS THE APP IN FRONT AND THE FIELD FOCUSED.
    from happy.system import macos

    bring_forward(win)
    AXUIElementSetAttributeValue(control.element, "AXFocused", True)
    if not add:
        macos.press("cmd+a")
    macos.paste(text)
    time.sleep(0.1)
    return (attr(control.element, "AXValue") or "") == wanted


def menu(win, path):
    """Chooses a menu bar item by its path, like ["File", "Export…"]; the path walked, or Failed."""
    from ApplicationServices import AXUIElementPerformAction

    bar = attr(win.root, "AXMenuBar")
    if bar is None:
        raise Failed(f"{win.app} has no menu bar to use.")
    level, walked, item = bar, [], None
    for step in path:
        items = [c for c in menu_items(level) if attr(c, "AXTitle")]
        item = best(items, step, lambda c: attr(c, "AXTitle"))
        if item is None:
            names = ", ".join(attr(c, "AXTitle") for c in items if attr(c, "AXTitle"))[:400]
            raise Failed(f"No {step} in {' > '.join(walked) or 'the menu bar'} of {win.app}. There is: {names}.")
        walked.append(attr(item, "AXTitle"))
        level = item
    if attr(item, "AXEnabled") is False:
        raise Failed(f"{' > '.join(walked)} is greyed out in {win.app} right now.")
    if AXUIElementPerformAction(item, "AXPress") != 0:
        raise Failed(f"{' > '.join(walked)} could not be chosen in {win.app}.")
    return walked


def menu_items(level):
    children = attr(level, "AXChildren") or []
    # A MENU BAR ITEM HOLDS ONE MENU, AND THE MENU HOLDS THE ITEMS.
    if len(children) == 1 and attr(children[0], "AXRole") == "AXMenu":
        return attr(children[0], "AXChildren") or []
    return children


def best(items, words, name):
    wanted = clean(words)
    for test in (lambda n: n == wanted, lambda n: n.startswith(wanted), lambda n: wanted in n):
        for item in items:
            if test(clean(name(item) or "")):
                return item
    return None


def clean(text):
    return " ".join(str(text).lower().replace("…", "").replace("...", "").split())


def scroll(win, where, inside=None):
    """Scrolls the window's biggest scrolling area, or the one holding a named control; the new position from 0 to 1."""
    from ApplicationServices import AXUIElementSetAttributeValue

    areas = controls(win, roles={"AXScrollArea", "AXWebArea"}, budget=3000) if inside is None else []
    area = inside or max(areas, key=lambda c: (c.frame[2] * c.frame[3]) if c.frame else 0, default=None)
    bar = attr(area.element, "AXVerticalScrollBar") if area else None
    if bar is not None and isinstance(attr(bar, "AXValue"), (int, float)):
        now = float(attr(bar, "AXValue"))
        target = {"top": 0.0, "bottom": 1.0, "up": max(0.0, now - 0.25), "down": min(1.0, now + 0.25)}[where]
        AXUIElementSetAttributeValue(bar, "AXValue", target)
        time.sleep(0.1)
        return float(attr(bar, "AXValue") or target)
    # WEB PAGES HAVE NO SCROLL BAR TO SET, SO THE WHEEL TURNS OVER THEM WITH THE APP IN FRONT.
    box = area.frame if area and area.frame else attrs_frame(win.element)
    if box is None:
        raise Failed(f"Nothing in {win.app} scrolls.")
    bring_forward(win)
    wheel(box, where)
    return None


def attrs_frame(element):
    a = attrs(element, ["AXPosition", "AXSize"])
    return frame(a["AXPosition"], a["AXSize"])


def wheel(box, where):
    from Quartz import CGEventCreateScrollWheelEvent, CGEventPost, CGEventSetLocation, kCGHIDEventTap, kCGScrollEventUnitPixel

    lines = {"up": 600, "down": -600, "top": 100000, "bottom": -100000}[where]
    event = CGEventCreateScrollWheelEvent(None, kCGScrollEventUnitPixel, 1, lines)
    CGEventSetLocation(event, (box[0] + box[2] / 2, box[1] + box[3] / 2))
    CGEventPost(kCGHIDEventTap, event)
    time.sleep(0.2)


def focused_field(win):
    """The field the keyboard is in, inside this app, or None."""
    element = attr(win.root, "AXFocusedUIElement")
    if element is None:
        return None
    a = attrs(element, ASKED)
    if a["AXRole"] not in FIELDS:
        return None
    value = a["AXValue"] if isinstance(a["AXValue"], str) else ""
    return Control(a["AXRole"], a["AXTitle"] or a["AXDescription"] or KINDS[a["AXRole"]], value, True,
                   frame(a["AXPosition"], a["AXSize"]), element, 0)


def title(win):
    return attr(win.element, "AXTitle") or ""


def alive(control):
    return attr(control.element, "AXRole") is not None
