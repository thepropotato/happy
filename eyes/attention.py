"""WHAT IS IN FRONT, WHAT HAS THE CARET, AND WHERE THE POINTER IS.

THESE ARE THE CHEAP SENSES. THEY COST NO PICTURE AND NO MODEL, AND THEY ARE HOW
HAPPY NOTICES THAT SOMEONE ELSE HAS TOUCHED THE COMPUTER: A DIFFERENT
APPLICATION IN FRONT, OR A POINTER THAT IS NOT WHERE IT WAS LEFT.
"""

import sys

MACOS = "darwin"
WINDOWS = "win32"

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

        # THROUGH wording() FOR THE INVISIBLE DIRECTION MARKS: THE APPLICATION
        # IN FRONT IS REPORTED AS "‎WhatsApp", NOT "WhatsApp", AND THAT NAME IS
        # COMPARED AGAINST WHAT A PERSON SAID.
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

        # A WINDOW WITH NO TITLE IS COMMON AND IS NOT AN ANSWER. THE MAIN WINDOW
        # AND THEN THE FIRST ONE ARE TRIED BEFORE GIVING UP.
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


def caret():
    """WHAT HAS THE KEYBOARD, IN WORDS, OR "". TYPING GOES WHEREVER THIS IS."""
    if on_mac():
        from eyes.asking import mac_attribute
        from eyes.naming import wording

        _, pid = front()

        if pid is None:
            return ""

        from ApplicationServices import AXUIElementCreateApplication

        app = AXUIElementCreateApplication(pid)
        focused = mac_attribute(app, "AXFocusedUIElement")

        if focused is None:
            return ""

        return (
            wording(mac_attribute(focused, "AXTitle"))
            or wording(mac_attribute(focused, "AXDescription"))
            or wording(mac_attribute(focused, "AXRole"))
        )

    if on_windows():
        try:
            from comtypes.client import CreateObject, GetModule

            GetModule("UIAutomationCore.dll")

            from comtypes.gen.UIAutomationClient import CUIAutomation, IUIAutomation

            automation = CreateObject(CUIAutomation, interface=IUIAutomation)
            focused = automation.GetFocusedElement()

            return str(focused.CurrentName or "") if focused else ""
        except Exception:
            return ""

    return ""


def pointer():
    """WHERE THE POINTER IS, IN THE COORDINATES IT MOVES IN."""
    try:
        from pynput.mouse import Controller

        x, y = Controller().position

        return int(x), int(y)
    except Exception:  # NO DISPLAY, OR NO PERMISSION TO ASK.
        return 0, 0
