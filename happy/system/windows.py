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


def battery():
    out = powershell("$b = Get-CimInstance Win32_Battery; if ($b) { \"$($b.EstimatedChargeRemaining) $($b.BatteryStatus) $($b.EstimatedRunTime)\" }")
    if not out:
        return None
    percent, status, minutes = (out.split() + ["", ""])[:3]
    left = int(minutes) if minutes.isdigit() and int(minutes) < 10000 else 0
    return int(percent), status in ("2", "6", "7", "8", "9"), f"{left // 60}:{left % 60:02d}" if left else ""


def wifi():
    out = powershell("netsh wlan show interfaces")
    state = next((line.split(":", 1)[1].strip() for line in out.splitlines() if line.strip().startswith("State")), "")
    name = next((line.split(":", 1)[1].strip() for line in out.splitlines() if line.strip().startswith("SSID")), "")
    if not state:
        raise Failed("this PC has no Wi-Fi")
    return state != "disconnected" or bool(name), name


def set_wifi(on):
    try:
        powershell(f'netsh interface set interface name="Wi-Fi" admin={"enabled" if on else "disabled"}')
    except Failed as error:
        raise Failed(f"Windows needs administrator rights to switch the Wi-Fi ({error})") from None


def get_clipboard():
    return powershell("Get-Clipboard -Raw")


def set_clipboard(text):
    subprocess.run(["clip"], input=text.encode("utf-16-le"), check=True)


def power(action):
    if action == "sleep":
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
    else:
        subprocess.run(["shutdown", "/r" if action == "restart" else "/s", "/t", "0"])


def trash(path):
    """Sends a file to the Recycle Bin; the bin keeps where it came from, so that is what is returned."""
    from ctypes import wintypes

    class Operation(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", ctypes.c_uint), ("pFrom", wintypes.LPCWSTR),
                    ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]

    # FO_DELETE WITH FOF_ALLOWUNDO, NO CONFIRMATION AND NO PROGRESS WINDOW.
    operation = Operation(None, 3, str(path) + "\0", None, 0x40 | 0x10 | 0x400 | 0x4, False, None, None)
    if ctypes.windll.shell32.SHFileOperationW(ctypes.byref(operation)) != 0:
        raise Failed("the Recycle Bin refused it")
    return str(path)


def untrash(held, original):
    found = powershell(
        "$bin = (New-Object -ComObject Shell.Application).NameSpace(10); "
        f"$item = $bin.Items() | Where-Object {{ (Join-Path $bin.GetDetailsOf($_, 1) $_.Name) -eq '{original}' }} | Select-Object -First 1; "
        "if ($item) { $item.InvokeVerb('undelete'); 'ok' }")
    if found != "ok":
        raise Failed("it is no longer in the Recycle Bin; it may have been emptied")


STARTUP = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Startup/Happy.vbs"


def start_at_login(on, command, folder):
    """A script in the Startup folder that starts Happy with no console window when the person logs in."""
    if not on:
        STARTUP.unlink(missing_ok=True)
        return
    windowless = [command[0].replace("python.exe", "pythonw.exe")] + command[1:]
    line = " ".join(f'""{part}""' for part in windowless)
    script = f'Set shell = CreateObject("WScript.Shell")\nshell.CurrentDirectory = "{folder}"\nshell.Run "{line}", 0\n'
    if STARTUP.exists() and STARTUP.read_text() == script:
        return
    STARTUP.parent.mkdir(parents=True, exist_ok=True)
    STARTUP.write_text(script)
