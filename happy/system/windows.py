"""Windows controls, written to the same shape as the macOS ones; untested on real hardware so far."""

import ctypes
import os
import subprocess
import time
from pathlib import Path


class Failed(RuntimeError):
    pass


def powershell(script, timeout=15):
    done = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True,
                          text=True, timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if done.returncode != 0:
        raise Failed(done.stderr.strip() or "PowerShell failed")
    return done.stdout.strip()


def get_brightness():
    import screen_brightness_control as sbc

    return int(sbc.get_brightness(display=0)[0])


def set_brightness(percent):
    import screen_brightness_control as sbc

    sbc.set_brightness(max(0, min(100, int(percent))), display=0)


def get_keyboard_light():
    raise Failed("Windows has no standard way to reach the keyboard backlight")


def set_keyboard_light(percent):
    raise Failed("Windows has no standard way to reach the keyboard backlight")


def endpoint():
    from pycaw.pycaw import AudioUtilities

    return AudioUtilities.GetSpeakers().EndpointVolume


def get_volume():
    volume = endpoint()
    return round(volume.GetMasterVolumeLevelScalar() * 100), bool(volume.GetMute())


def set_volume(percent):
    endpoint().SetMasterVolumeLevelScalar(max(0, min(100, int(percent))) / 100, None)


def set_muted(muted):
    endpoint().SetMute(1 if muted else 0, None)


VK = {
    "toggle": 0xB3, "next": 0xB0, "previous": 0xB1,
    "ctrl": 0x11, "control": 0x11, "shift": 0x10, "alt": 0x12, "win": 0x5B, "cmd": 0x11,
    "return": 0x0D, "enter": 0x0D, "tab": 0x09, "space": 0x20, "backspace": 0x08, "delete": 0x2E,
    "escape": 0x1B, "esc": 0x1B, "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    **{f"f{n}": 0x6F + n for n in range(1, 13)},
}


def tap(code, up=False):
    ctypes.windll.user32.keybd_event(code, 0, 2 if up else 0, 0)


def media_key(action):
    tap(VK[action])
    tap(VK[action], up=True)


def press(combo):
    parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
    codes = []
    for part in parts:
        if part in VK:
            codes.append(VK[part])
        elif len(part) == 1:
            codes.append(ctypes.windll.user32.VkKeyScanW(ord(part)) & 0xFF)
        else:
            raise Failed(f"unknown key {part}")
    for code in codes:
        tap(code)
    for code in reversed(codes):
        tap(code, up=True)
        time.sleep(0.01)


def paste(text):
    subprocess.run(["clip"], input=text.encode("utf-16-le"), check=True)
    press("ctrl+v")


def frontmost():
    user32 = ctypes.windll.user32
    window = user32.GetForegroundWindow()
    buffer = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(window, buffer, 512)
    return buffer.value.rsplit(" - ", 1)[-1]


def front_window_title():
    user32 = ctypes.windll.user32
    buffer = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(user32.GetForegroundWindow(), buffer, 512)
    return buffer.value


def running_apps():
    out = powershell("Get-Process | Where-Object {$_.MainWindowTitle} | Select-Object -ExpandProperty ProcessName")
    return sorted(set(out.splitlines()))


def installed_apps():
    found = {}
    for root in (Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")), Path(os.environ.get("APPDATA", ""))):
        menu = root / "Microsoft/Windows/Start Menu/Programs"
        for link in menu.rglob("*.lnk"):
            found.setdefault(link.stem, str(link))
    return found


def open_app(path_or_name):
    os.startfile(path_or_name)


def quit_app(name):
    powershell(f"Get-Process | Where-Object {{$_.MainWindowTitle -like '*{name}*' -or $_.ProcessName -like '*{name}*'}} | ForEach-Object {{ $_.CloseMainWindow() | Out-Null }}")


def open_path(path, app=None, reveal=False):
    if reveal:
        subprocess.run(["explorer", "/select,", str(path)])
    elif app:
        subprocess.Popen([app, str(path)], shell=True)
    else:
        os.startfile(str(path))


def spotlight(query, folders_only=False, limit=12):
    words = query.lower().split()
    hits = []
    for base in ("Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos", "source", "projects"):
        root = Path.home() / base
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if any(part.startswith(".") or part == "node_modules" for part in path.parts):
                continue
            if folders_only and not path.is_dir():
                continue
            if all(w in path.name.lower() for w in words):
                hits.append(str(path))
                if len(hits) >= 200:
                    return hits
    return hits


def screenshot():
    raise Failed("screenshots are not wired up on Windows yet")


def selected_text():
    return ""


def trusted():
    return True
