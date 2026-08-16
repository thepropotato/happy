"""WHAT THE SYSTEM HAS TO LET THE EARS DO, AND ASKING IT TO."""

import ctypes
import ctypes.util
import sys

MACOS = "darwin"
WINDOWS = "win32"

MICROPHONE = "microphone"
KEYS = "keys"

PANES = {
    MICROPHONE: "Privacy_Microphone",
    KEYS: "Privacy_ListenEvent",
}

MICROPHONE_HINT = "Hearing you at all, whether you say his name or hold the key."
KEYS_HINT = "Noticing the hold to talk key while another window is in front."

# WHAT AVCaptureDevice ANSWERS: NOT ASKED, REFUSED BY POLICY, REFUSED, ALLOWED.
UNASKED = 0
ALLOWED = 3

# kIOHIDRequestTypeListenEvent, AND ZERO BACK MEANS GRANTED.
LISTENING = 1
GRANTED = 0


def on_mac():
    return sys.platform == MACOS


def on_windows():
    return sys.platform == WINDOWS


def microphone():
    """TRUE, FALSE, OR None WHERE THIS SYSTEM DOES NOT GATE THE MICROPHONE."""
    if not on_mac():
        return None  # WINDOWS GATES THIS IN SETTINGS, WITH NOTHING TO READ IT BY.

    try:
        import AVFoundation

        asked = AVFoundation.AVCaptureDevice.authorizationStatusForMediaType_(
            AVFoundation.AVMediaTypeAudio
        )

        return None if asked == UNASKED else asked == ALLOWED
    except Exception:
        return None


def ask_microphone():
    """THE SYSTEM'S OWN DIALOG. IT ANSWERS ON ANOTHER THREAD, SO NOTHING IS WAITED ON."""
    if not on_mac():
        return False

    try:
        import AVFoundation

        AVFoundation.AVCaptureDevice.requestAccessForMediaType_completionHandler_(
            AVFoundation.AVMediaTypeAudio, lambda granted: None
        )

        return True
    except Exception:
        return False


def iokit():
    """THE FRAMEWORK THE KEY PERMISSION LIVES IN, WHICH PYOBJC DOES NOT WRAP."""
    where = ctypes.util.find_library("IOKit")

    return ctypes.CDLL(where) if where else None


def keys():
    """TRUE, FALSE, OR None WHERE WATCHING KEYS IS NOT GATED."""
    if not on_mac():
        return None

    try:
        found = iokit()

        if found is None:
            return None

        found.IOHIDCheckAccess.restype = ctypes.c_int
        found.IOHIDCheckAccess.argtypes = [ctypes.c_uint32]

        return found.IOHIDCheckAccess(LISTENING) == GRANTED
    except Exception:
        return None


def ask_keys():
    if not on_mac():
        return False

    try:
        found = iokit()

        if found is None:
            return False

        found.IOHIDRequestAccess.restype = ctypes.c_bool
        found.IOHIDRequestAccess.argtypes = [ctypes.c_uint32]

        return bool(found.IOHIDRequestAccess(LISTENING))
    except Exception:
        return False


def gated():
    """WINDOWS WITHHOLDS THE MICROPHONE TOO, IT JUST WILL NOT SAY SO TO A DESKTOP PROGRAM."""
    return on_mac() or on_windows()


EVERY = (
    {
        "name": MICROPHONE,
        "label": "Microphone",
        "hint": MICROPHONE_HINT,
        "gated": gated,
        "allowed": microphone,
        "ask": ask_microphone,
        "pane": PANES[MICROPHONE],
    },
    {
        "name": KEYS,
        "label": "Input monitoring",
        "hint": KEYS_HINT,
        "gated": on_mac,
        "allowed": keys,
        "ask": ask_keys,
        "pane": PANES[KEYS],
    },
)
