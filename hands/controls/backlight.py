"""THE MAC'S OWN BRIGHTNESS, ASKED FOR DIRECTLY.

THE HOMEBREW `brightness` HELPER IS BUILT ON IODisplay CALLS THAT APPLE SILICON
NO LONGER ANSWERS, SO ON EVERY RECENT MAC IT IS BOTH MISSING AND, ONCE
INSTALLED, WRONG. TELLING SOMEONE TO GO AND BREW IT WAS THEREFORE NOT EVEN
HELPFUL ADVICE.

WHAT THE SLIDER IN SETTINGS AND THE KEYS ON THE KEYBOARD BOTH GO THROUGH IS
DisplayServices. IT IS PRIVATE, WHICH IS WHY EVERY CALL HERE IS WRAPPED: A
FRAMEWORK APPLE NEVER PROMISED US IS ALLOWED TO VANISH, AND THAT SHOULD COST A
FALLBACK TO THE BRIGHTNESS KEYS RATHER THAN A CRASH.

LEVELS HERE ARE FRACTIONS FROM 0 TO 1, WHICH IS WHAT THE FRAMEWORK SPEAKS. THE
PERCENTAGES A PERSON SAYS OUT LOUD ARE screen.py'S BUSINESS.
"""

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
    """THE SCREEN A PERSON MEANS WHEN THEY SAY "THE SCREEN", OR None.

    THE ONE WITH THE MENU BAR ON IT. AN EXTERNAL MONITOR IS ITS OWN DEVICE WITH
    ITS OWN BUTTONS AND IS NOT ALWAYS WILLING TO BE ASKED.
    """
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
