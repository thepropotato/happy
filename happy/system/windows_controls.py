"""Reading and working the controls inside any Windows app through UI Automation; the same shape as macos_controls, untested on real hardware so far."""

import time
from dataclasses import dataclass

from happy.system.windows import Failed

FIELDS = {"EditControl", "ComboBoxControl", "DocumentControl"}
PRESSABLE = {"ButtonControl", "HyperlinkControl", "MenuItemControl", "SplitButtonControl", "CheckBoxControl", "RadioButtonControl",
             "TabItemControl", "ListItemControl", "TreeItemControl", "DataItemControl", "SliderControl", "SpinnerControl",
             "TextControl", "ImageControl"} | FIELDS
LISTED = PRESSABLE - {"TextControl", "ImageControl", "ListItemControl", "TreeItemControl", "DataItemControl", "DocumentControl"}
KINDS = {"ButtonControl": "button", "HyperlinkControl": "link", "MenuItemControl": "menu item", "SplitButtonControl": "button",
         "CheckBoxControl": "checkbox", "RadioButtonControl": "option", "TabItemControl": "tab", "ListItemControl": "list item",
         "TreeItemControl": "tree item", "DataItemControl": "row", "SliderControl": "slider", "SpinnerControl": "stepper",
         "TextControl": "text", "ImageControl": "image", "EditControl": "text field", "ComboBoxControl": "combo box",
         "DocumentControl": "document"}


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
        return KINDS.get(self.role, self.role.removesuffix("Control").lower())

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


def auto():
    import uiautomation

    return uiautomation


def process_name(pid):
    import ctypes
    from pathlib import Path

    kernel = ctypes.windll.kernel32
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return ""
    try:
        buffer, size = ctypes.create_unicode_buffer(1024), ctypes.c_ulong(1024)
        return Path(buffer.value).stem if kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)) else ""
    finally:
        kernel.CloseHandle(handle)


def window(app=""):
    """The window to work in: the named app's top window, or the one in front."""
    import os

    ua = auto()
    front = ua.GetForegroundControl()
    front = front.GetTopLevelControl() if front else None
    if app:
        wanted = app.lower().strip()
        tops = [w for w in ua.GetRootControl().GetChildren() if w.ControlTypeName == "WindowControl" and w.Name]
        named = [(w, f"{w.Name} {process_name(w.ProcessId)}".lower()) for w in tops]
        target = next((w for test in (lambda n: wanted in n, lambda n: any(p in n for p in wanted.split()))
                       for w, n in named if test(n)), None)
        if target is None:
            raise Failed(f"{app} is not open.")
    else:
        target = front
    if target is None:
        raise Failed("No window is in front.")
    if target.ProcessId == os.getpid():
        raise Failed("Happy's own panel is in front, so there is nothing of theirs to work in. Name the app.")
    name = process_name(target.ProcessId) or target.Name
    return Window(name, target.Name or "", target.ProcessId, target, target,
                  bool(front) and front.NativeWindowHandle == target.NativeWindowHandle)


def value_of(control):
    try:
        ok, pattern = True, control.GetValuePattern()
        return pattern.Value if ok and pattern else ""
    except Exception:
        return ""


def controls(win, roles=PRESSABLE, budget=6000):
    """Every control in the window with something to call it by, top to bottom, left to right."""
    ua = auto()
    found, walked = [], 0
    for element, depth in ua.WalkControl(win.element, includeTop=False, maxDepth=40):
        walked += 1
        if walked > budget:
            break
        role = element.ControlTypeName
        if role not in roles:
            continue
        value = value_of(element) if role in FIELDS else ""
        label = (element.Name or element.HelpText or "").strip() or (KINDS[role] if role in FIELDS else "")
        if not (label or value):
            continue
        box = element.BoundingRectangle
        rect = (box.left, box.top, box.width(), box.height()) if box and box.width() else None
        found.append(Control(role, label or value[:80], value, bool(element.IsEnabled), rect, element, depth))
    found.sort(key=lambda c: (round(c.frame[1] / 8), c.frame[0]) if c.frame else (1e9, 0))
    return found


def press(control, win):
    """Presses a control the way the app itself would, falling back to a real click."""
    element = control.element
    for get, act in (("GetInvokePattern", "Invoke"), ("GetTogglePattern", "Toggle"), ("GetSelectionItemPattern", "Select"),
                     ("GetExpandCollapsePattern", "Expand"), ("GetLegacyIAccessiblePattern", "DoDefaultAction")):
        try:
            pattern = getattr(element, get)()
            if pattern:
                getattr(pattern, act)()
                return "pressed"
        except Exception:
            continue
    bring_forward(win)
    element.Click(simulateMove=False)
    return "clicked"


def bring_forward(win):
    if not win.front:
        win.element.SetActive()
        win.element.SetTopmost(False)
        time.sleep(0.3)
        win.front = True


def set_text(control, text, win, add=False):
    """Puts text in a field and reads it back; True when the field holds it."""
    wanted = (control.value + text) if add else text
    try:
        control.element.GetValuePattern().SetValue(wanted)
        time.sleep(0.1)
        if value_of(control.element) == wanted:
            return True
    except Exception:
        pass
    from happy.system import windows

    bring_forward(win)
    control.element.SetFocus()
    if not add:
        windows.press("ctrl+a")
    windows.paste(text)
    time.sleep(0.1)
    return value_of(control.element) == wanted


def menu(win, path):
    """Chooses a menu item by its path, like ["File", "Save As"]; the path walked, or Failed."""
    ua = auto()
    level, walked, item = win.element, [], None
    for step in path:
        items = [c for c, _ in ua.WalkControl(level, maxDepth=3) if c.ControlTypeName == "MenuItemControl" and c.Name]
        item = best(items, step, lambda c: c.Name)
        if item is None:
            names = ", ".join(c.Name for c in items)[:400]
            raise Failed(f"No {step} in {' > '.join(walked) or 'the menu bar'} of {win.app}. There is: {names}.")
        walked.append(item.Name)
        if step is not path[-1]:
            try:
                item.GetExpandCollapsePattern().Expand()
            except Exception:
                item.Click(simulateMove=False)
            time.sleep(0.3)
            # AN OPENED MENU IS ITS OWN WINDOW UNDER THE DESKTOP, NOT INSIDE THE APP'S.
            level = ua.GetRootControl()
    if not item.IsEnabled:
        raise Failed(f"{' > '.join(walked)} is greyed out in {win.app} right now.")
    press(Control("MenuItemControl", item.Name, "", True, None, item, 0), win)
    return walked


def best(items, words, name):
    wanted = clean(words)
    for test in (lambda n: n == wanted, lambda n: n.startswith(wanted), lambda n: wanted in n):
        for item in items:
            if test(clean(name(item) or "")):
                return item
    return None


def clean(text):
    return " ".join(str(text).lower().replace("…", "").replace("...", "").replace("&", "").split())


def scroll(win, where, inside=None):
    """Scrolls the window's biggest scrolling area; the new position from 0 to 1, or None when it was turned by the wheel."""
    ua = auto()
    areas = [c for c, _ in ua.WalkControl(win.element, maxDepth=30) if c.GetPattern(ua.PatternId.ScrollPattern)]
    area = max(areas, key=lambda c: c.BoundingRectangle.width() * c.BoundingRectangle.height(), default=None)
    if area is not None:
        pattern = area.GetScrollPattern()
        if pattern.VerticallyScrollable:
            now = pattern.VerticalScrollPercent / 100
            target = {"top": 0.0, "bottom": 1.0, "up": max(0.0, now - 0.25), "down": min(1.0, now + 0.25)}[where]
            # -1 LEAVES THE SIDEWAYS POSITION WHERE IT IS.
            pattern.SetScrollPercent(-1, target * 100)
            time.sleep(0.1)
            return pattern.VerticalScrollPercent / 100
    bring_forward(win)
    over = area or win.element
    turns = 50 if where in ("top", "bottom") else 10
    over.WheelDown(turns) if where in ("down", "bottom") else over.WheelUp(turns)
    return None


def focused_field(win):
    """The field the keyboard is in, inside this app, or None."""
    element = auto().GetFocusedControl()
    if element is None or element.ProcessId != win.pid or element.ControlTypeName not in FIELDS:
        return None
    return Control(element.ControlTypeName, element.Name or KINDS[element.ControlTypeName], value_of(element), True, None, element, 0)


def title(win):
    return win.element.Name or ""


def alive(control):
    try:
        return control.element.Exists(0, 0)
    except Exception:
        return False
