"""THE MAC'S OWN SCREEN BRIGHTNESS, ASKED FOR DIRECTLY."""

import ctypes
import ctypes.util
from ctypes import byref, c_float, c_int

FRAMEWORK = "/System/Library/PrivateFrameworks/DisplayServices.framework/DisplayServices"

# None MEANS NOT TRIED YET; False MEANS TRIED AND NOT THERE.
loaded = None


def library():
    """DisplayServices WITH ITS TWO FUNCTIONS DESCRIBED, OR None."""
    global loaded

    if loaded is not None:
        return loaded or None

    try:
        found = ctypes.CDLL(FRAMEWORK)

        found.DisplayServicesGetBrightness.argtypes = [c_int, ctypes.POINTER(c_float)]
        found.DisplayServicesGetBrightness.restype = c_int
        found.DisplayServicesSetBrightness.argtypes = [c_int, c_float]
        found.DisplayServicesSetBrightness.restype = c_int
    except (OSError, AttributeError):
        loaded = False

        return None

    loaded = found

    return found


def display():
    """THE SCREEN A PERSON MEANS WHEN THEY SAY "THE SCREEN", OR None."""
    try:
        core = ctypes.CDLL(
            ctypes.util.find_library("CoreGraphics")
            or "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics"
        )
        core.CGMainDisplayID.restype = c_int
    except (OSError, AttributeError):
        return None

    return core.CGMainDisplayID()


def level():
    """THE BRIGHTNESS NOW, FROM 0 TO 1, OR None WHEN IT CANNOT BE READ."""
    found, screen = library(), display()

    if found is None or screen is None:
        return None

    held = c_float(0)

    try:
        if found.DisplayServicesGetBrightness(screen, byref(held)) != 0:
            return None
    except Exception:
        return None

    return held.value


def put(fraction):
    """SET THE BRIGHTNESS, FROM 0 TO 1. TRUE WHEN IT ACTUALLY MOVED."""
    found, screen = library(), display()

    if found is None or screen is None:
        return False

    try:
        return found.DisplayServicesSetBrightness(screen, c_float(fraction)) == 0
    except Exception:
        return False
