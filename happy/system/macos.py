"""macOS controls, reached through the system frameworks rather than extra installs."""

import ctypes
import ctypes.util
import os
import subprocess
import time
from functools import cache
from pathlib import Path


class Failed(RuntimeError):
    pass


def osascript(script, timeout=15):
    done = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout)
    if done.returncode != 0:
        raise Failed(done.stderr.strip() or "AppleScript failed")
    return done.stdout.strip()


@cache
def display_services():
    cg = ctypes.CDLL(ctypes.util.find_library("CoreGraphics"))
    cg.CGMainDisplayID.restype = ctypes.c_uint32
    ds = ctypes.CDLL("/System/Library/PrivateFrameworks/DisplayServices.framework/DisplayServices")
    ds.DisplayServicesSetBrightness.argtypes = [ctypes.c_uint32, ctypes.c_float]
    return cg, ds


def get_brightness():
    cg, ds = display_services()
    value = ctypes.c_float()
    if ds.DisplayServicesGetBrightness(cg.CGMainDisplayID(), ctypes.byref(value)) != 0:
        raise Failed("this display does not report its brightness")
    return round(value.value * 100)


def set_brightness(percent):
    cg, ds = display_services()
    if ds.DisplayServicesSetBrightness(cg.CGMainDisplayID(), max(0.0, min(1.0, percent / 100))) != 0:
        raise Failed("this display does not let its brightness be set")


@cache
def keyboard_client():
    import objc
    from Foundation import NSBundle

    NSBundle.bundleWithPath_("/System/Library/PrivateFrameworks/CoreBrightness.framework").load()
    client = objc.lookUpClass("KeyboardBrightnessClient").alloc().init()
    ids = client.copyKeyboardBacklightIDs()
    if not ids:
        raise Failed("this Mac has no keyboard backlight")
    return client, ids[0]


def get_keyboard_light():
    client, kid = keyboard_client()
    return round(client.brightnessForKeyboard_(kid) * 100)


def set_keyboard_light(percent):
    client, kid = keyboard_client()
    level = max(0.0, min(1.0, percent / 100))
    client.enableAutoBrightness_forKeyboard_(False, kid)
    client.setBrightness_fadeSpeed_commit_forKeyboard_(level, 350, True, kid)


def get_volume():
    settings = osascript("get volume settings")
    parts = dict(p.strip().split(":", 1) for p in settings.split(","))
    return int(parts["output volume"]), parts["output muted"].strip() == "true"


def set_volume(percent):
    osascript(f"set volume output volume {max(0, min(100, int(percent)))}")


def set_muted(muted):
    osascript(f"set volume output muted {'true' if muted else 'false'}")


MEDIA_KEYS = {"toggle": 16, "next": 17, "previous": 18}


def media_key(action):
    from AppKit import NSEvent
    from Quartz import CGEventPost, kCGHIDEventTap

    key = MEDIA_KEYS[action]
    for state in (0xA, 0xB):
        event = NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
            14, (0, 0), state << 8, 0, 0, None, 8, (key << 16) | (state << 8), -1
        )
        CGEventPost(kCGHIDEventTap, event.CGEvent())


KEYCODES = {
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9, "b": 11, "q": 12,
    "w": 13, "e": 14, "r": 15, "y": 16, "t": 17, "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23,
    "=": 24, "9": 25, "7": 26, "-": 27, "8": 28, "0": 29, "]": 30, "o": 31, "u": 32, "[": 33, "i": 34,
    "p": 35, "l": 37, "j": 38, "'": 39, "k": 40, ";": 41, "\\": 42, ",": 43, "/": 44, "n": 45, "m": 46,
    ".": 47, "`": 50, "return": 36, "enter": 36, "tab": 48, "space": 49, "delete": 51, "backspace": 51,
    "escape": 53, "esc": 53, "forwarddelete": 117, "home": 115, "end": 119, "pageup": 116,
    "pagedown": 121, "left": 123, "right": 124, "down": 125, "up": 126,
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97, "f7": 98, "f8": 100, "f9": 101,
    "f10": 109, "f11": 103, "f12": 111,
}
MODIFIERS = {"cmd": 1 << 20, "command": 1 << 20, "shift": 1 << 17, "ctrl": 1 << 18, "control": 1 << 18,
             "alt": 1 << 19, "option": 1 << 19, "opt": 1 << 19, "fn": 1 << 23}


def press(combo):
    """Presses a combination like "cmd+shift+t" in whatever app is in front."""
    from Quartz import CGEventCreateKeyboardEvent, CGEventPost, CGEventSetFlags, kCGHIDEventTap

    parts = [p.strip().lower() for p in combo.replace(" ", "").split("+") if p.strip()]
    flags = 0
    for part in parts[:-1]:
        if part not in MODIFIERS:
            raise Failed(f"unknown modifier {part}")
        flags |= MODIFIERS[part]
    key = parts[-1]
    if key not in KEYCODES:
        raise Failed(f"unknown key {key}")
    for down in (True, False):
        event = CGEventCreateKeyboardEvent(None, KEYCODES[key], down)
        CGEventSetFlags(event, flags)
        CGEventPost(kCGHIDEventTap, event)
        time.sleep(0.01)


def paste(text):
    """Types text by pasting it, then puts back whatever was on the clipboard."""
    from AppKit import NSPasteboard, NSPasteboardTypeString

    board = NSPasteboard.generalPasteboard()
    before = board.stringForType_(NSPasteboardTypeString)
    board.clearContents()
    board.setString_forType_(text, NSPasteboardTypeString)
    press("cmd+v")
    time.sleep(0.25)
    if before is not None:
        board.clearContents()
        board.setString_forType_(before, NSPasteboardTypeString)


def front_is_happy():
    from AppKit import NSWorkspace

    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    return bool(app) and app.processIdentifier() == os.getpid()


def frontmost():
    from AppKit import NSWorkspace

    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    return app.localizedName() if app else ""


def front_window_title():
    from Quartz import CGWindowListCopyWindowInfo, kCGNullWindowID, kCGWindowListOptionOnScreenOnly

    owner = frontmost()
    for window in CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID) or []:
        if window.get("kCGWindowOwnerName") == owner and window.get("kCGWindowLayer") == 0:
            return window.get("kCGWindowName") or ""
    return ""


def running_apps():
    from AppKit import NSWorkspace

    return [a.localizedName() for a in NSWorkspace.sharedWorkspace().runningApplications()
            if a.activationPolicy() == 0 and a.localizedName()]


APP_DIRS = ["/Applications", "/System/Applications", "/System/Applications/Utilities",
            str(Path.home() / "Applications"), "/Applications/Utilities"]


def installed_apps():
    found = {}
    for folder in APP_DIRS:
        root = Path(folder)
        if not root.exists():
            continue
        for app in list(root.glob("*.app")) + list(root.glob("*/*.app")):
            found.setdefault(app.stem, str(app))
    found.setdefault("Finder", "/System/Library/CoreServices/Finder.app")
    return found


def open_app(path_or_name):
    done = subprocess.run(["open", "-a", path_or_name], capture_output=True, text=True)
    if done.returncode != 0:
        raise Failed(done.stderr.strip() or f"could not open {path_or_name}")


def quit_app(name):
    osascript(f'tell application "{name}" to quit')


def open_path(path, app=None, reveal=False):
    args = ["open"] + (["-R"] if reveal else []) + (["-a", app] if app else []) + [str(path)]
    done = subprocess.run(args, capture_output=True, text=True)
    if done.returncode != 0:
        raise Failed(done.stderr.strip() or f"could not open {path}")


def spotlight(query, folders_only=False, limit=12):
    """Finds files by name through Spotlight, most recently used first."""
    kind = ' && kMDItemContentType == "public.folder"' if folders_only else ""
    words = " && ".join(f'kMDItemFSName == "*{w}*"cd' for w in query.split())
    done = subprocess.run(["mdfind", "-onlyin", str(Path.home()), f"({words}){kind}"],
                          capture_output=True, text=True, timeout=10)
    hits = [h for h in done.stdout.splitlines() if h and "/Library/" not in h and "/." not in h
            and "/node_modules/" not in h and "/.venv/" not in h]
    return hits[:200]


def screenshot():
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as file:
        path = file.name
    done = subprocess.run(["screencapture", "-x", "-C", "-t", "png", path], capture_output=True)
    data = Path(path).read_bytes() if done.returncode == 0 and Path(path).exists() else b""
    Path(path).unlink(missing_ok=True)
    if not data:
        raise Failed("could not take a screenshot; give the terminal Screen Recording permission")
    return data


def selected_text():
    """The text selected in the front app, read through Accessibility."""
    from ApplicationServices import (AXUIElementCopyAttributeValue, AXUIElementCreateSystemWide,
                                     kAXFocusedUIElementAttribute, kAXSelectedTextAttribute)

    # ASKING HAPPY'S OWN WINDOW RUNS ITS WEB VIEW ON THIS THREAD, AND CHROMIUM KILLS THE APP FOR IT.
    if front_is_happy():
        return ""
    system = AXUIElementCreateSystemWide()
    err, focused = AXUIElementCopyAttributeValue(system, kAXFocusedUIElementAttribute, None)
    if err or focused is None:
        return ""
    err, text = AXUIElementCopyAttributeValue(focused, kAXSelectedTextAttribute, None)
    return "" if err or not text else str(text)


def trusted():
    from ApplicationServices import AXIsProcessTrusted

    return bool(AXIsProcessTrusted())


def output_device():
    """The sound output macOS is using right now, by name, read fresh from CoreAudio."""
    return sound_device("dOut")


def input_device():
    """The microphone macOS is using right now, by name, read fresh from CoreAudio."""
    return sound_device("dIn ")


def sound_devices(scope):
    """The names of every device with sound going "inpt" (microphones) or "outp" (speakers), read fresh from CoreAudio."""
    import struct

    class Address(ctypes.Structure):
        _fields_ = [("selector", ctypes.c_uint32), ("scope", ctypes.c_uint32), ("element", ctypes.c_uint32)]

    def where(selector, kind="glob"):
        return ctypes.byref(Address(*struct.unpack(">II", (selector + kind).encode()), 0))

    audio = ctypes.CDLL(ctypes.util.find_library("CoreAudio"))
    foundation = ctypes.CDLL(ctypes.util.find_library("CoreFoundation"))
    foundation.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
    size = ctypes.c_uint32(0)
    if audio.AudioObjectGetPropertyDataSize(ctypes.c_uint32(1), where("dev#"), 0, None, ctypes.byref(size)):
        return []
    ids = (ctypes.c_uint32 * (size.value // 4))()
    audio.AudioObjectGetPropertyData(ctypes.c_uint32(1), where("dev#"), 0, None, ctypes.byref(size), ids)
    names = []
    for device in ids:
        streams = ctypes.c_uint32(0)
        audio.AudioObjectGetPropertyDataSize(ctypes.c_uint32(device), where("stm#", scope), 0, None, ctypes.byref(streams))
        name = ctypes.c_void_p()
        length = ctypes.c_uint32(ctypes.sizeof(name))
        if not streams.value or audio.AudioObjectGetPropertyData(ctypes.c_uint32(device), where("lnam"), 0, None, ctypes.byref(length), ctypes.byref(name)) or not name.value:
            continue
        text = ctypes.create_string_buffer(256)
        foundation.CFStringGetCString(name, text, 256, 0x08000100)
        foundation.CFRelease(name)
        names.append(text.value.decode())
    return names


def sound_device(selector):
    import struct

    class Address(ctypes.Structure):
        _fields_ = [("selector", ctypes.c_uint32), ("scope", ctypes.c_uint32), ("element", ctypes.c_uint32)]

    def code(text):
        return struct.unpack(">I", text.encode())[0]

    audio = ctypes.CDLL(ctypes.util.find_library("CoreAudio"))
    foundation = ctypes.CDLL(ctypes.util.find_library("CoreFoundation"))
    foundation.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]

    def read(owner, selector, kind):
        where = Address(code(selector), code("glob"), 0)
        value = kind()
        size = ctypes.c_uint32(ctypes.sizeof(value))
        failed = audio.AudioObjectGetPropertyData(ctypes.c_uint32(owner), ctypes.byref(where), 0, None, ctypes.byref(size), ctypes.byref(value))
        return None if failed else value.value

    device = read(1, selector, ctypes.c_uint32)
    name = read(device, "lnam", ctypes.c_void_p) if device else None
    if not name:
        return ""
    text = ctypes.create_string_buffer(256)
    foundation.CFStringGetCString(name, text, 256, 0x08000100)
    foundation.CFRelease(ctypes.c_void_p(name))
    return text.value.decode()


def cursor_from_background():
    """Lets this app set the cursor while another app is in front, which is all Happy ever is."""
    try:
        services = ctypes.CDLL("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
        foundation = ctypes.CDLL(ctypes.util.find_library("CoreFoundation"))
        services._CGSDefaultConnection.restype = ctypes.c_int
        foundation.CFStringCreateWithCString.restype = ctypes.c_void_p
        foundation.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
        connection = services._CGSDefaultConnection()
        key = foundation.CFStringCreateWithCString(None, b"SetsCursorInBackground", 0x08000100)
        true = ctypes.c_void_p.in_dll(foundation, "kCFBooleanTrue")
        services.CGSSetConnectionProperty.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
        services.CGSSetConnectionProperty(connection, connection, key, true)
        return True
    except Exception:
        return False


def battery():
    """(percent, charging, time left) from pmset, or None on a Mac without a battery."""
    import re

    out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
    match = re.search(r"(\d+)%; ([\w ]+);(?: (\d+:\d+) remaining)?", out)
    if not match:
        return None
    state = match.group(2).strip()
    return int(match.group(1)), state in ("charging", "charged", "finishing charge") or "AC Power" in out, match.group(3) or ""


def wifi_device():
    import re

    out = subprocess.run(["networksetup", "-listallhardwareports"], capture_output=True, text=True).stdout
    match = re.search(r"Hardware Port: (?:Wi-Fi|AirPort)\nDevice: (\w+)", out)
    if not match:
        raise Failed("this Mac has no Wi-Fi")
    return match.group(1)


def wifi():
    """(on, network name) for the Wi-Fi."""
    device = wifi_device()
    power = subprocess.run(["networksetup", "-getairportpower", device], capture_output=True, text=True).stdout
    if not power.strip().endswith("On"):
        return False, ""
    route = subprocess.run(["ipconfig", "getsummary", device], capture_output=True, text=True).stdout
    name = next((line.split(" : ", 1)[1].strip() for line in route.splitlines() if line.strip().startswith("SSID :")), "")
    # RECENT MACOS HIDES THE NETWORK'S NAME FROM ANY APP WITHOUT LOCATION ACCESS.
    return True, "" if name == "<redacted>" else name


def set_wifi(on):
    subprocess.run(["networksetup", "-setairportpower", wifi_device(), "on" if on else "off"], check=True)


def get_clipboard():
    return subprocess.run(["pbpaste"], capture_output=True, text=True).stdout


def set_clipboard(text):
    subprocess.run(["pbcopy"], input=text, text=True, check=True)


def power(action):
    """Sleep, restart or shut down the way the menu does, so apps still ask about unsaved work."""
    if action == "sleep":
        subprocess.run(["pmset", "sleepnow"], capture_output=True)
        return
    osascript(f'tell application "System Events" to {"restart" if action == "restart" else "shut down"}')


def trash(path):
    """Moves a file to the Trash the way Finder does, and returns where it ended up."""
    from Foundation import NSFileManager, NSURL

    moved, landed, error = NSFileManager.defaultManager().trashItemAtURL_resultingItemURL_error_(
        NSURL.fileURLWithPath_(str(path)), None, None)
    if not moved:
        raise Failed(str(error.localizedDescription()) if error else "the Trash refused it")
    return landed.path()


def untrash(held, original):
    import shutil

    if not Path(held).exists():
        raise Failed("it is no longer in the Trash; it may have been emptied")
    Path(original).parent.mkdir(parents=True, exist_ok=True)
    shutil.move(held, original)


AGENT = Path.home() / "Library" / "LaunchAgents" / "com.happy.agent.plist"


def start_at_login(on, command, folder):
    """A LaunchAgent that starts Happy when the person logs in, carrying this PATH so it finds the same tools."""
    import os
    import plistlib

    if not on:
        AGENT.unlink(missing_ok=True)
        return
    wanted = {"Label": "com.happy.agent", "ProgramArguments": command, "WorkingDirectory": str(folder),
              "RunAtLoad": True, "ProcessType": "Interactive",
              "EnvironmentVariables": {"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
              "StandardOutPath": str(Path.home() / ".happy" / "happy.out"),
              "StandardErrorPath": str(Path.home() / ".happy" / "happy.out")}
    if AGENT.exists() and plistlib.loads(AGENT.read_bytes()) == wanted:
        return
    AGENT.parent.mkdir(parents=True, exist_ok=True)
    AGENT.write_bytes(plistlib.dumps(wanted))
