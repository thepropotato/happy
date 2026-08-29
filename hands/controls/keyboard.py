"""THE LIGHT UNDER THE KEYS, WHICH IS NOT THE SCREEN'S."""

import ctypes
import ctypes.util
from ctypes import c_bool, c_char_p, c_float, c_uint64, c_void_p

from hands.controls.commands import clamp, on_mac

FRAMEWORK = "/System/Library/PrivateFrameworks/CoreBrightness.framework/CoreBrightness"

CLIENT = b"KeyboardBrightnessClient"

# THE BUILT IN KEYBOARD. AN EXTERNAL ONE LIGHTS ITSELF AND IS NOT ASKED HERE.
BUILT_IN = 1

# None MEANS NOT TRIED YET; False MEANS TRIED AND NOT THERE.
loaded = None


def client():
    """ONE KeyboardBrightnessClient AND THE TWO CALLS TYPED, OR None."""
    global loaded

    if loaded is not None:
        return loaded or None

    try:
        objc = ctypes.CDLL(ctypes.util.find_library("objc"))
        ctypes.CDLL(FRAMEWORK)

        objc.objc_getClass.restype = c_void_p
        objc.objc_getClass.argtypes = [c_char_p]
        objc.sel_registerName.restype = c_void_p
        objc.sel_registerName.argtypes = [c_char_p]

        found = objc.objc_getClass(CLIENT)

        if not found:
            loaded = False

            return None

        # objc_msgSend IS CAST PER SIGNATURE: A FLOAT RETURN AND A FLOAT ARGUMENT DO NOT
        # TRAVEL IN THE SAME REGISTERS AS THE POINTERS THE DEFAULT PROTOTYPE DECLARES.
        start = ctypes.cast(objc.objc_msgSend, ctypes.CFUNCTYPE(c_void_p, c_void_p, c_void_p))
        instance = start(start(found, objc.sel_registerName(b"alloc")),
                         objc.sel_registerName(b"init"))

        if not instance:
            loaded = False

            return None

        loaded = (
            instance,
            ctypes.cast(objc.objc_msgSend, ctypes.CFUNCTYPE(c_float, c_void_p, c_void_p, c_uint64)),
            ctypes.cast(objc.objc_msgSend,
                        ctypes.CFUNCTYPE(c_bool, c_void_p, c_void_p, c_float, c_uint64)),
            objc.sel_registerName(b"brightnessForKeyboard:"),
            objc.sel_registerName(b"setBrightness:forKeyboard:"),
        )
    except (OSError, AttributeError):
        loaded = False

        return None

    return loaded


def level():
    """THE BACKLIGHT NOW, FROM 0 TO 1, OR None WHEN IT CANNOT BE READ."""
    found = client()

    if found is None:
        return None

    instance, read, _, asking, _ = found

    try:
        return read(instance, asking, BUILT_IN)
    except Exception:
        return None


def put(fraction):
    """SET THE BACKLIGHT, FROM 0 TO 1. TRUE WHEN IT ACTUALLY MOVED."""
    found = client()

    if found is None:
        return False

    instance, _, write, _, setting = found

    try:
        return bool(write(instance, setting, c_float(fraction), BUILT_IN))
    except Exception:
        return False


# WINDOWS LIGHTS ITS KEYS THROUGH EACH MAKER'S OWN UTILITY, AND NO SYSTEM CALL REACHES THEM.
ELSEWHERE = (
    "This computer does not let me set the keyboard backlight. "
    "The keys on the keyboard itself do it."
)

NONE_HERE = (
    "This Mac has no keyboard backlight I can reach, so the keys on the keyboard "
    "itself are the way to change it."
)


def status():
    if not on_mac():
        return ELSEWHERE

    now = level()

    if now is None:
        return NONE_HERE

    return f"The keyboard backlight is {round(now * 100)} percent."


def set_level(wanted):
    value = clamp(wanted)

    if value is None:
        return "The keyboard backlight has to be a number between zero and one hundred."

    if not on_mac():
        return ELSEWHERE

    if not put(value / 100):
        return NONE_HERE

    return f"Keyboard backlight set to {value} percent."


def change(step):
    if not on_mac():
        return ELSEWHERE

    now = level()

    if now is None:
        return NONE_HERE

    return set_level(clamp(round(now * 100) + step))
