"""WHAT IS IN FRONT, WHAT HAS THE CARET, AND WHERE THE POINTER IS.

THESE ARE THE CHEAP SENSES. THEY COST NO PICTURE AND NO MODEL, AND THEY ARE HOW
HAPPY NOTICES THAT SOMEONE ELSE HAS TOUCHED THE COMPUTER: A DIFFERENT
APPLICATION IN FRONT, OR A POINTER THAT IS NOT WHERE IT WAS LEFT.
"""

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
    """WHY THE TREE CANNOT BE READ, OR None WHEN IT CAN.

    MACOS REFUSES BY HANDING BACK AN EMPTY TREE RATHER THAN AN ERROR, WHICH
    WOULD OTHERWISE READ AS AN APPLICATION THAT DESCRIBES NOTHING.
    """
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


def front():
    """THE APPLICATION IN FRONT, AS (NAME, HANDLE). THE HANDLE IS WHAT EACH
    SYSTEM WANTS BACK WHEN ASKED TO DESCRIBE IT: A PROCESS ON MACOS, A WINDOW
    ON WINDOWS."""
    if on_mac():
        try:
            from AppKit import NSWorkspace

            running = NSWorkspace.sharedWorkspace().frontmostApplication()
        except Exception:
            return "", None

        if running is None:
            return "", None

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

            return psutil.Process(pid.value).name().removesuffix(".exe"), handle
        except Exception:
            return "", None

    return "", None


def doing():
    """WHAT THE PERSON IS IN AND WHAT IT IS CALLED, IN ONE LINE, OR "".

    THE CHEAPEST ANSWER THERE IS TO "WHAT IS THIS PERSON DOING": FORTY
    MILLISECONDS, NO PICTURE AND NO MODEL. THE TITLE IS THE PART THAT MEANS
    ANYTHING — THE FILE, THE PAGE, THE EPISODE — SO A WINDOW WITH NO TITLE IS
    ONLY WORTH THE NAME OF THE APPLICATION.
    """
    for name, handle, title in pile():
        if not title:
            try:
                title = window(handle)
            except Exception:
                title = ""

        if not title or title == name:
            return f"{name} is in front"

        return f'{name} is in front, and the window is "{title}"'

    return ""


def windows():
    """EVERY ORDINARY WINDOW, FRONT TO BACK, AS (NAME, TITLE), DUPLICATES GONE.

    doing() IS THE FRONT ONE AND THIS IS ALL OF THEM, WHICH IS NOT THE SAME
    QUESTION: WHAT SOMEBODY IS DOING IS OFTEN NOT THE WINDOW ON TOP. A VIDEO
    PLAYS ON BEHIND THE THING BEING TYPED INTO, AND A CHAT SITS TWO WINDOWS BACK.
    """
    found = []
    seen = set()

    for name, handle, title in everything():
        pair = (name, "" if title == name else title)

        if pair in seen:
            continue

        seen.add(pair)
        found.append(pair)

    return found


def everything():
    """EVERY WINDOW WORTH NAMING, FRONT TO BACK, AS (NAME, HANDLE, TITLE).

    NOT pile(): THAT ONE ASKS MACOS FOR WHAT IS ON SCREEN, AND A CALL OR A VIDEO
    GONE FULLSCREEN IS A SPACE OF ITS OWN — SO ON-SCREEN-ONLY THEN SWEARS THE
    OTHER SIX WINDOWS ARE NOT OPEN. WINDOWS HAS NO SPACES AND ITS WALK DOWN THE
    PILE IS ALREADY EVERY TITLED WINDOW, SO THERE IT IS THE SAME LIST.
    """
    ours = {os.getpid(), os.getppid()}

    try:
        if on_mac():
            return mac_everything(ours)

        if on_windows():
            return windows_pile(ours)
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

        # ONE THAT NAMES ITSELF NOTHING IS FURNITURE: AN AUTOFILL BUBBLE, A LOGIN
        # PANEL, A HELPER. doing() CAN ASK ACCESSIBILITY FOR THE ONE IN FRONT,
        # BUT A WHOLE LIST CANNOT WITHOUT A ROUND TRIP PER WINDOW.
        if not title:
            continue

        found.append((name, None, title))

    return found


def pile():
    """EVERY ORDINARY WINDOW, FRONT TO BACK, AS (NAME, HANDLE, TITLE), SKIPPING
    HAPPY'S OWN. THE HANDLE IS WHAT window() WANTS BACK.

    NOT front(): HIS PANEL COMES UP OVER EVERYTHING THE SECOND HIS NAME IS SAID
    AND STAYS ACTIVE WHILE ANYBODY TYPES INTO IT, SO THE SYSTEM'S OWN ANSWER TO
    WHAT IS IN FRONT IS HIMSELF. A MENU BAR AND A STATUS DOT ARE IN FRONT TOO.
    WHAT SOMEBODY IS DOING IS THE FIRST WINDOW THAT IS NONE OF THAT.
    """
    ours = {os.getpid(), os.getppid()}  # THE PANEL IS ELECTRON, AND IT STARTED THIS.

    try:
        if on_mac():
            return mac_pile(ours)

        if on_windows():
            return windows_pile(ours)
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
    """THE TITLE OF THE WINDOW IN FRONT. handle IS A PROCESS ON MACOS AND A
    WINDOW ON WINDOWS, WHICHEVER front() HANDED BACK."""
    if on_mac():
        from ApplicationServices import AXUIElementCreateApplication

        from eyes.asking import mac_attribute
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
