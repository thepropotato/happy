"""ASKING EACH SYSTEM WHAT IT PUT ON THE SCREEN."""

from eyes.naming import (
    MAC_FOLDED,
    MAC_KINDS,
    MAC_TICKABLE,
    WINDOWS_KINDS,
    plain,
    wording,
)
from eyes.shapes import Element

# A DEEPLY NESTED APPLICATION WOULD OTHERWISE HAND BACK TENS OF THOUSANDS OF GROUPS.
MAX_DEPTH = 16
MAX_VISITS = 2500

# WHERE AN APPLICATION'S WINDOWS ACTUALLY ARE.
MAC_ROOTS = ("AXChildren", "AXWindows", "AXFocusedWindow", "AXMainWindow")

def mac_attribute(element, name):
    from ApplicationServices import AXUIElementCopyAttributeValue

    try:
        error, value = AXUIElementCopyAttributeValue(element, name, None)
    except Exception:
        return None

    return value if error == 0 else None


def mac_box(element):
    from ApplicationServices import AXValueGetValue, kAXValueTypeCGPoint, kAXValueTypeCGSize

    place = mac_attribute(element, "AXPosition")
    size = mac_attribute(element, "AXSize")

    if place is None or size is None:
        return None

    try:
        got, point = AXValueGetValue(place, kAXValueTypeCGPoint, None)
        fine, span = AXValueGetValue(size, kAXValueTypeCGSize, None)
    except Exception:
        return None

    if not (got and fine):
        return None

    return int(point.x), int(point.y), int(span.width), int(span.height)


def mac_element(element, role):
    box = mac_box(element)

    if box is None:
        return None

    raw = mac_attribute(element, "AXValue")
    ticked = bool(raw) if role in MAC_TICKABLE and isinstance(raw, (int, float)) else None

    label = (
        wording(mac_attribute(element, "AXTitle"))
        or wording(mac_attribute(element, "AXDescription"))
        or wording(mac_attribute(element, "AXHelp"))
    )

    return Element(
        kind=MAC_KINDS.get(role, plain(role)),
        label=label,
        value="" if ticked is not None else wording(raw),
        left=box[0],
        top=box[1],
        width=box[2],
        height=box[3],
        enabled=mac_attribute(element, "AXEnabled") is not False,
        focused=mac_attribute(element, "AXFocused") is True,
        ticked=ticked,
    )


def mac_roots(app):
    """THE TOP OF EVERY TREE WORTH WALKING, EACH ONE ONCE."""
    from CoreFoundation import CFEqual

    roots = []

    for name in MAC_ROOTS:
        got = mac_attribute(app, name)

        for element in got if isinstance(got, (list, tuple)) else [got] if got else []:
            if not any(CFEqual(element, seen) for seen in roots):
                roots.append(element)

    return roots


def mac_elements(pid):
    """EVERY ELEMENT ONE RUNNING APPLICATION IS WILLING TO DESCRIBE."""
    from ApplicationServices import AXUIElementCreateApplication

    found, visits = [], [0]

    def walk(element, depth):
        if depth > MAX_DEPTH or visits[0] >= MAX_VISITS:
            return

        visits[0] += 1
        role = wording(mac_attribute(element, "AXRole"))

        if not role:
            return

        made = mac_element(element, role)

        if made is not None:
            if made.width > 0 and made.height > 0:
                found.append(made)
            elif role in MAC_FOLDED:
                return

        for child in mac_attribute(element, "AXChildren") or ():
            walk(child, depth + 1)

    for root in mac_roots(AXUIElementCreateApplication(pid)):
        walk(root, 1)  # DEPTH 1: THE APPLICATION'S CHILDREN.

    return found


def windows_pattern(element, identifier, interface):
    try:
        got = element.GetCurrentPattern(identifier)

        return got.QueryInterface(interface) if got else None
    except Exception:
        return None


def windows_element(raw):
    from comtypes.gen.UIAutomationClient import (
        IUIAutomationTogglePattern,
        IUIAutomationValuePattern,
    )

    edge = raw.CurrentBoundingRectangle
    left, top = int(edge.left), int(edge.top)
    width, height = int(edge.right) - left, int(edge.bottom) - top

    toggle = windows_pattern(raw, 10015, IUIAutomationTogglePattern)
    holder = windows_pattern(raw, 10002, IUIAutomationValuePattern)

    # 0 IS OFF AND 1 IS ON. 2 IS THE THIRD STATE, WHICH IS NEITHER.
    state = None if toggle is None else toggle.CurrentToggleState
    ticked = None if state in (None, 2) else bool(state)

    return Element(
        kind=WINDOWS_KINDS.get(raw.CurrentControlType, "control"),
        label=wording(raw.CurrentName),
        value="" if ticked is not None else wording(holder and holder.CurrentValue),
        left=left,
        top=top,
        width=width,
        height=height,
        enabled=bool(raw.CurrentIsEnabled),
        focused=bool(raw.CurrentHasKeyboardFocus),
        ticked=ticked,
    )


def windows_elements(handle):
    """EVERY ELEMENT THE WINDOW IN FRONT IS WILLING TO DESCRIBE."""
    from comtypes.client import CreateObject, GetModule

    GetModule("UIAutomationCore.dll")

    from comtypes.gen.UIAutomationClient import CUIAutomation, IUIAutomation

    automation = CreateObject(CUIAutomation, interface=IUIAutomation)
    root = automation.ElementFromHandle(handle) if handle else automation.GetRootElement()
    walker = automation.RawViewWalker
    found, visits = [], [0]

    # SIBLINGS IN A LOOP, NOT BY RECURSION: A THOUSAND ROWS WOULD BLOW THE STACK.
    def walk(first, depth):
        element = first

        while element is not None and visits[0] < MAX_VISITS:
            visits[0] += 1

            try:
                made = windows_element(element)
                hidden = element.CurrentIsOffscreen
            except Exception:
                break

            # MACOS ONLY IMPLIES OFFSCREEN, BY HANDING BACK A BOX WITH NO SIZE.
            if made.width > 0 and made.height > 0 and not hidden:
                found.append(made)

            if depth < MAX_DEPTH:
                walk(walker.GetFirstChildElement(element), depth + 1)

            element = walker.GetNextSiblingElement(element)

    walk(walker.GetFirstChildElement(root), 0)

    return found
