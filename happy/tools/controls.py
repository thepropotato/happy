"""Screen brightness, sound, the keyboard light, whatever is playing, and the machine itself: battery, Wi-Fi, clipboard and power."""

import os
import re
import subprocess
import sys
import time
from typing import Annotated, Callable, Literal

from happy.config import Config, SPEECH_SPEEDS, speech_speed
from happy.system import Failed, native
from happy.tools import tool

Level = Annotated[int, "set it to exactly this, 0 to 100"]
Change = Annotated[Literal["up", "down"], "turn it up or down instead of setting a level"]
By = Annotated[int, "how much to turn it up or down by, 1 to 100; 10 if not said; a negative number means down"]
on_speed: Callable[[float], None] | None = None


@tool(label="Speaking speed")
def set_speech_speed(speed: float | None = None, change: Literal["up", "down"] | None = None):
    """Set Happy's speaking speed, keeping the pitch, or move one step up or down."""
    cfg = Config()
    value = speech_speed(cfg.get("speech_speed"))
    if change:
        index = SPEECH_SPEEDS.index(value) + (1 if change == "up" else -1)
        value = SPEECH_SPEEDS[max(0, min(len(SPEECH_SPEEDS) - 1, index))]
    elif speed is not None:
        value = speech_speed(speed)
    cfg.set("speech_speed", value)
    cfg.save()
    if on_speed is not None:
        on_speed(value)
    return f"Speaking at {value:g}x."


def adjust(name, read, write, level, change, by):
    """Sets or nudges a 0-100 control, then reads it back, so the answer is what actually happened."""
    before = read()
    if not change and level is None and by:
        change = "down" if by < 0 else "up"
    if change:
        after = before + (abs(by or 10) if change == "up" else -abs(by or 10))
    elif level is not None:
        after = level
    else:
        return f"{name} is {before}%."
    write(max(0, min(100, after)))
    now = read()
    moved = "up" if now > before else "down" if now < before else "unchanged"
    if moved == "unchanged":
        return f"{name} stayed at {now}% (it was already {'as high' if now >= 100 else 'as low' if now <= 0 else 'there'})."
    return f"{name} went {moved} from {before}% to {now}%."


@tool(label="Brightness {change}{level}")
def set_brightness(level: Level = None, change: Change = None, by: By = None):
    """Set the screen brightness to a level, or turn it up or down. With nothing given, says what it is."""
    return adjust("Brightness", native.get_brightness, native.set_brightness, level, change, by)


@tool(label="Volume {change}{level}")
def set_volume(level: Level = None, change: Change = None, by: By = None,
               muted: Annotated[bool, "true to mute, false to unmute"] = None):
    """Set the sound volume to a level, turn it up or down, or mute and unmute. With nothing given, says what it is."""
    if muted is not None:
        native.set_muted(muted)
        if level is None and change is None:
            return "Muted." if native.get_volume()[1] else "Unmuted."
    result = adjust("Volume", lambda: native.get_volume()[0], native.set_volume, level, change, by)
    current, is_muted = native.get_volume()
    if is_muted and current > 0 and muted is None and (level or change == "up"):
        native.set_muted(False)
    return result + (" It is muted." if native.get_volume()[1] and level is None and change is None else "")


@tool(label="Keyboard light {change}{level}")
def set_keyboard_light(level: Level = None, change: Change = None, by: By = None):
    """Set the keyboard backlight to a level, or turn it up or down. With nothing given, says what it is."""
    return adjust("Keyboard light", native.get_keyboard_light, native.set_keyboard_light, level, change, by)


def playing_apps():
    """Apps sending sound to a speaker right now, read from macOS power assertions."""
    if sys.platform != "darwin":
        return None
    out = subprocess.run(["pmset", "-g", "assertions"], capture_output=True, text=True).stdout
    pids = set()
    for block in out.split("\n   pid ")[1:]:
        resources = re.search(r"Resources: (.*)", block)
        sounding = "com.apple.audio." in block and resources and "audio-in" not in resources.group(1)
        if sounding or "audio-out" in block:
            pids.update(int(p) for p in re.findall(r"Created for PID: (\d+)", block))
    pids.discard(os.getpid())
    apps = set()
    for pid in pids:
        command = subprocess.run(["ps", "-o", "comm=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
        match = re.search(r"([^/]+)\.app/", command)
        apps.add(match.group(1) if match else os.path.basename(command))
    return sorted(a for a in apps if a)


@tool(label="Media: {action}")
def media(action: Literal["pause", "play", "toggle", "next", "previous"]):
    """Pause, play, skip or go back in whatever video or music is playing, in any app or browser tab."""
    if action in ("next", "previous"):
        native.media_key(action)
        return f"Skipped to the {action} track."
    playing = playing_apps()
    if action == "pause" and playing == []:
        return "Nothing is playing, so there was nothing to pause."
    if action == "play" and playing:
        return f"{', '.join(playing)} is already playing."
    native.media_key("toggle")
    if action == "toggle":
        return "Pressed play/pause."
    return f"Paused {', '.join(playing)}." if action == "pause" and playing else ("Paused." if action == "pause" else "Playing.")


@tool(label="{action}")
def computer(action: Literal["lock", "sleep_display", "dark_mode", "light_mode"]):
    """Lock the computer, turn the display off, or switch between dark and light mode."""
    if sys.platform != "darwin":
        if action == "lock":
            import ctypes

            ctypes.windll.user32.LockWorkStation()
            return "Locked."
        raise Failed(f"{action} is not wired up on this system yet")
    if action == "lock":
        native.press("ctrl+cmd+q")
        return "Locked."
    if action == "sleep_display":
        subprocess.run(["pmset", "displaysleepnow"])
        return "Display is off."
    dark = "true" if action == "dark_mode" else "false"
    native.osascript(f'tell application "System Events" to tell appearance preferences to set dark mode to {dark}')
    return "Dark mode on." if dark == "true" else "Light mode on."


@tool(label="Checking the battery")
def battery():
    """How much battery is left, whether it is charging, and how long it will last."""
    found = native.battery()
    if found is None:
        return "This computer has no battery; it runs on mains power."
    percent, charging, left = found
    hours, _, minutes = left.partition(":")
    lasts = f", about {int(hours)}h {int(minutes)}m left" if left and left != "0:00" and not charging else ""
    return f"Battery is at {percent}%, {'charging' if charging else 'not charging'}{lasts}."


@tool(label="Wi-Fi {action}")
def wifi(action: Literal["status", "on", "off"] = "status"):
    """Whether the Wi-Fi is on and which network it is on, or turn it on or off."""
    if action != "status":
        native.set_wifi(action == "on")
        time.sleep(2)
    on, name = native.wifi()
    if not on:
        return "Wi-Fi is off."
    return f"Wi-Fi is on{', connected to ' + name if name else ''}."


@tool(label="Clipboard: {action}")
def clipboard(action: Literal["read", "write"] = "read",
              text: Annotated[str, "what to put on the clipboard, for write"] = ""):
    """Read what is copied on the clipboard, or copy some text onto it."""
    if action == "write":
        native.set_clipboard(text)
        return "Copied to the clipboard."
    held = native.get_clipboard()
    return f"The clipboard holds:\n{held[:4000]}" if held.strip() else "The clipboard is empty."


# SAID FIRST, DONE AFTER: RESTART AND SHUT DOWN WAIT LONG ENOUGH TO BE HEARD AND STOPPED.
POWER_DELAY = 10
pending = None


def cancel_power():
    """Stops a restart or shut down that has been announced but not done yet."""
    global pending
    if pending and pending.is_alive():
        pending.cancel()
        pending = None
        return True
    return False


@tool(label="{action}")
def power(action: Literal["sleep", "restart", "shut_down", "cancel"]):
    """Put the computer to sleep, restart it or shut it down. Restart and shut down wait 10 seconds so they can be stopped; "cancel" stops one."""
    global pending
    import threading

    if action == "cancel":
        return "Cancelled; the computer stays on." if cancel_power() else "Nothing was about to restart or shut down."
    if action == "sleep":
        native.power("sleep")
        return "Going to sleep."
    cancel_power()
    pending = threading.Timer(POWER_DELAY, native.power, args=(action,))
    pending.daemon = True
    pending.start()
    verb = "Restarting" if action == "restart" else "Shutting down"
    return f"{verb} in {POWER_DELAY} seconds; apps will ask about anything unsaved. Say stop to cancel."
