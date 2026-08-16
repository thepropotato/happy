"""WHAT THE SYSTEM HAS TO LET THE EYES DO, AND ASKING IT TO."""

import sys

MACOS = "darwin"
WINDOWS = "win32"

SCREEN = "screen"
CONTROLS = "controls"

# THE PANE IN SYSTEM SETTINGS THAT HOLDS THE SWITCH, FOR SOMEBODY WHO SAID NO ONCE.
PANES = {
    SCREEN: "Privacy_ScreenCapture",
    CONTROLS: "Privacy_Accessibility",
}

SCREEN_HINT = "Taking a picture of the screen, which is how Happy looks at anything."
CONTROLS_HINT = "Reading the buttons and fields in other windows, and pressing them."


def on_mac():
    return sys.platform == MACOS


def on_windows():
    return sys.platform == WINDOWS


def screen():
    """TRUE, FALSE, OR None WHERE THIS SYSTEM DOES NOT GATE LOOKING AT ALL."""
    if not on_mac():
        return None  # WINDOWS LETS ANY PROGRAM READ THE SCREEN WITHOUT ASKING.

    try:
        from Quartz import CGPreflightScreenCaptureAccess

        return bool(CGPreflightScreenCaptureAccess())
    except Exception:
        return None


def ask_screen():
    """THE SYSTEM'S OWN DIALOG, WHICH IT WILL ONLY EVER PUT UP ONCE."""
    if not on_mac():
        return False

    try:
        from Quartz import CGRequestScreenCaptureAccess

        return bool(CGRequestScreenCaptureAccess())
    except Exception:
        return False


def controls():
    """TRUE, FALSE, OR None WHERE NOTHING IS BEING WITHHELD."""
    if on_windows():
        return None  # NOTHING TO GRANT: comtypes EITHER IMPORTS OR IT DOES NOT.

    if not on_mac():
        return None

    try:
        from ApplicationServices import AXIsProcessTrusted

        return bool(AXIsProcessTrusted())
    except Exception:
        return None


def ask_controls():
    """ASK BY CHECKING WITH THE PROMPT TURNED ON, WHICH IS THE ONLY WAY THERE IS."""
    if not on_mac():
        return False

    try:
        from ApplicationServices import AXIsProcessTrustedWithOptions
        from ApplicationServices import kAXTrustedCheckOptionPrompt

        return bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True}))
    except Exception:
        return False


# NAME, LABEL, WHAT IT IS FOR, WHETHER THIS SYSTEM WITHHOLDS IT AT ALL, HOW TO READ IT,
# HOW TO ASK, AND WHERE THE SWITCH IS FOR SOMEBODY WHO HAS TO GO AND FIND IT.
EVERY = (
    {
        "name": SCREEN,
        "label": "Screen recording",
        "hint": SCREEN_HINT,
        "gated": on_mac,
        "allowed": screen,
        "ask": ask_screen,
        "pane": PANES[SCREEN],
    },
    {
        "name": CONTROLS,
        "label": "Accessibility",
        "hint": CONTROLS_HINT,
        "gated": on_mac,
        "allowed": controls,
        "ask": ask_controls,
        "pane": PANES[CONTROLS],
    },
)
