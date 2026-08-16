"""WHAT IS IN FRONT, WHAT HAS THE CARET, AND WHERE THE POINTER IS."""

import os
import sys

MACOS = "darwin"
WINDOWS = "win32"

LEAST = 100  # PIXELS EITHER WAY. SMALLER THAN THIS IS FURNITURE, NOT A WINDOW.

GW_HWNDNEXT = 2  # THE NEXT WINDOW DOWN THE PILE.

DENIED = (
    "I cannot read this window's controls. Accessibility has to be allowed for "
    "whatever runs Happy: on macOS in System Settings, Privacy and Security, "
    "Accessibility, then start Happy again."
)

UNSUPPORTED = "I can only read a window's controls on macOS and Windows."

MISSING_ON_WINDOWS = (
    "I cannot read this window's controls: comtypes is not installed. "
    "Get it with: pip install comtypes"
)


def on_mac():
    return sys.platform == MACOS


def on_windows():
    return sys.platform == WINDOWS


def allowed():
    """WHY THE TREE CANNOT BE READ, OR None WHEN IT CAN."""
    if on_mac():
        try:
            from ApplicationServices import AXIsProcessTrusted
        except ImportError:
            return "I cannot read this window's controls: pyobjc is not installed."

        return None if AXIsProcessTrusted() else DENIED

    if on_windows():
        try:
            import comtypes  # noqa: F401
        except ImportError:
            return MISSING_ON_WINDOWS

        return None

    return UNSUPPORTED


def ours():
    """THE PROCESSES HAPPY IS. THE PANEL IS ELECTRON, AND IT STARTED THIS."""
    return {os.getpid(), os.getppid()}


def front():
    """THE APPLICATION IN FRONT, AS (NAME, HANDLE), NEVER HAPPY HIMSELF.

    HIS PANEL IS ACTIVE WHENEVER ANYBODY IS TALKING TO HIM, SO THE SYSTEM'S OWN
    ANSWER TO WHAT IS IN FRONT WAS HIM, AND list_controls READ HIS TRANSCRIPT
    BACK AS THE SCREEN. pile() ALREADY SKIPS HIM, SO IT IS THE ANSWER INSTEAD.
    """
    if on_mac():
        try:
            from AppKit import NSWorkspace

            running = NSWorkspace.sharedWorkspace().frontmostApplication()
        except Exception:
            return "", None

        if running is None:
            return "", None

        if running.processIdentifier() in ours():
            return behind()

        # THROUGH wording() FOR INVISIBLE DIRECTION MARKS: THE NAME IN FRONT COMES
        # BACK AS "‎WhatsApp", NOT "WhatsApp".
        from eyes.naming import wording

        return wording(running.localizedName()), running.processIdentifier()

    if on_windows():
        try:
            import ctypes

            import psutil

            handle = ctypes.windll.user32.GetForegroundWindow()

            if not handle:
                return "", None

            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))

            if pid.value in ours():
                return behind()

            return psutil.Process(pid.value).name().removesuffix(".exe"), handle
        except Exception:
            return "", None

    return "", None


def behind():
    """THE FIRST WINDOW THAT IS NOT HAPPY, FOR WHEN HIS PANEL IS THE ACTIVE ONE."""
    for name, handle, _ in pile():
        return name, handle

    return "", None


def windows():
    """EVERY ORDINARY WINDOW ON EVERY DESKTOP, THE FRONT ONE FIRST, AS (NAME, TITLE)."""
    # everything() SORTS A FULLSCREEN WINDOW ON ANOTHER DESKTOP AHEAD OF THE ONE BEING
    # TYPED INTO, SO WHO IS IN FRONT IS ASKED FOR RATHER THAN TAKEN OFF THE TOP OF IT.
    name, handle = front()
    ahead = []
    behind = []
    seen = set()

    for other, who, title in everything():
        pair = (other, "" if title == other else title)

        if pair in seen:
            continue

        seen.add(pair)

        # THE FRONT APP'S FIRST WINDOW IS THE ONE THEY ARE LOOKING AT; ITS OTHERS ARE NOT.
        if who is not None and who == handle and not ahead:
            ahead.append(pair)
        else:
            behind.append(pair)

    # A WINDOW FULLSCREEN ON ANOTHER DESKTOP IS SOMETIMES LISTED AS UNTITLED FURNITURE
    # AND NOTHING ELSE, SO THE APP IN FRONT CAN BE MISSING FROM THIS ENTIRELY.
    if name and not ahead:
        ahead.append((name, titled(handle, name)))

    return ahead + behind


def document(handle=None):
    """THE FILE A WINDOW IS SHOWING, AS A PATH, ASKED OF THE APPLICATION ITSELF.

    A TITLE IS THE NAME OF A FILE AND NOT WHERE IT IS, SO ANYTHING THAT WANTS TO
    SEND, READ OR ATTACH WHAT IS OPEN HAS TO GO LOOKING FOR IT ON THE DISK. THIS
    IS THE ANSWER WITHOUT THE LOOKING, WHEREVER THE APPLICATION WILL GIVE IT.
    """
    if handle is None:
        handle = front()[1]

    if handle is None:
        return None

    if on_mac():
        return mac_document(handle)

    # WINDOWS HAS NO PROPERTY FOR THIS. WHAT THE WINDOW IS CALLED IS ALL THERE IS.
    return None


def mac_document(handle):
    """THE FOCUSED WINDOW'S AXDocument. AN ELECTRON APP HANDS BACK AN EMPTY ONE."""
    try:
        from ApplicationServices import AXUIElementCreateApplication

        from eyes.systems import mac_attribute
    except ImportError:
        return None

    app = AXUIElementCreateApplication(handle)
    window = mac_attribute(app, "AXFocusedWindow") or mac_attribute(app, "AXMainWindow")

    return filed(mac_attribute(window, "AXDocument")) if window is not None else None


def filed(said):
    """A file:// ADDRESS AS A PATH ON THIS DISK, OR None WHEN IT IS NEITHER."""
    from urllib.parse import unquote, urlparse

    said = str(said or "")

    if not said.startswith("file://"):
        return None

    return unquote(urlparse(said).path) or None


def titled(handle, name):
    """THE FRONT WINDOW'S TITLE, ASKED OF THE APPLICATION RATHER THAN OF THE SCREEN."""
    try:
        title = window(handle)
    except Exception:
        return ""

    return "" if title == name else title


def everything():
    """EVERY WINDOW WORTH NAMING, FRONT TO BACK, AS (NAME, HANDLE, TITLE)."""
    mine = ours()

    try:
        if on_mac():
            return mac_everything(mine)

        if on_windows():
            return windows_pile(mine)
    except Exception:
        return []

    return []


def mac_everything(ours):
    import Quartz

    from eyes.naming import wording

    listed = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionAll | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID,
    )

    found = []

    for each in listed or ():
        pid = each.get("kCGWindowOwnerPID")
        name = wording(each.get("kCGWindowOwnerName") or "")
        title = wording(each.get("kCGWindowName") or "")
        box = each.get("kCGWindowBounds") or {}

        if each.get("kCGWindowLayer") or not each.get("kCGWindowAlpha") or not name:
            continue

        if pid in ours or min(box.get("Width") or 0, box.get("Height") or 0) < LEAST:
            continue

        # ONE THAT NAMES ITSELF NOTHING IS FURNITURE: AN AUTOFILL BUBBLE, A LOGIN PANEL, A
        # HELPER.
        if not title:
            continue

        found.append((name, pid, title))

    return found


def pile():
    """EVERY ORDINARY WINDOW, FRONT TO BACK, AS (NAME, HANDLE, TITLE), SKIPPING HAPPY'S OWN."""
    mine = ours()

    try:
        if on_mac():
            return mac_pile(mine)

        if on_windows():
            return windows_pile(mine)
    except Exception:
        return []

    return []


def mac_pile(ours):
    import Quartz

    from eyes.naming import wording

    listed = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID,
    )

    found = []

    for each in listed or ():
        pid = each.get("kCGWindowOwnerPID")
        name = wording(each.get("kCGWindowOwnerName"))
        box = each.get("kCGWindowBounds") or {}

        # LAYER 0 IS WHERE AN APPLICATION KEEPS ITS WINDOWS; NO ALPHA IS DRAWN NOWHERE.
        if each.get("kCGWindowLayer") or not each.get("kCGWindowAlpha") or not name:
            continue

        if pid in ours or min(box.get("Width") or 0, box.get("Height") or 0) < LEAST:
            continue

        # THE TITLE COMES BACK EMPTY UNLESS THE SCREEN MAY BE RECORDED.
        found.append((name, pid, wording(each.get("kCGWindowName"))))

    return found


def windows_pile(ours):
    import ctypes

    import psutil

    user32 = ctypes.windll.user32
    found = []
    handle = user32.GetTopWindow(None)

    while handle:
        length = user32.GetWindowTextLengthW(handle)
        pid = ctypes.c_ulong()

        user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))

        # NO TITLE IS HOW WINDOWS DRAWS ITS OWN FURNITURE.
        if length and user32.IsWindowVisible(handle) and pid.value not in ours:
            hold = ctypes.create_unicode_buffer(length + 1)

            user32.GetWindowTextW(handle, hold, length + 1)

            try:
                name = psutil.Process(pid.value).name().removesuffix(".exe")
            except Exception:
                name = ""

            if name:
                found.append((name, handle, hold.value))

        handle = user32.GetWindow(handle, GW_HWNDNEXT)

    return found


def window(handle=None):
    """THE TITLE OF THE WINDOW IN FRONT."""
    if on_mac():
        from ApplicationServices import AXUIElementCreateApplication

        from eyes.systems import mac_attribute
        from eyes.naming import wording

        pid = handle if handle is not None else front()[1]

        if pid is None:
            return ""

        app = AXUIElementCreateApplication(pid)

        for attribute in ("AXFocusedWindow", "AXMainWindow"):
            title = wording(mac_attribute(mac_attribute(app, attribute), "AXTitle"))

            if title:
                return title

        for each in mac_attribute(app, "AXWindows") or ():
            title = wording(mac_attribute(each, "AXTitle"))

            if title:
                return title

        return ""

    if on_windows():
        try:
            import ctypes

            handle = handle or ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(handle) + 1
            hold = ctypes.create_unicode_buffer(length)
            ctypes.windll.user32.GetWindowTextW(handle, hold, length)

            return hold.value or ""
        except Exception:
            return ""

    return ""
