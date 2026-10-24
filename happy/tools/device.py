"""Screen brightness, sound, the keyboard light and whatever is playing."""

import os
import re
import subprocess
import sys
from typing import Annotated, Literal

from happy.platforms import Failed, system
from happy.tools import tool

Percent = Annotated[int, "0 to 100; with relative=true, the change instead, like 10 or -10"]
Relative = Annotated[bool, "true to change by percent rather than set it"]


def target(current, percent, relative):
    return max(0, min(100, current + percent if relative else percent))


@tool(label="Brightness {percent}")
def set_brightness(percent: Percent = None, relative: Relative = False):
    """Set the screen brightness, or leave percent out to hear what it is."""
    if percent is None:
        return f"Brightness is {system.get_brightness()}%."
    level = target(system.get_brightness() if relative else 0, percent, relative)
    system.set_brightness(level)
    return f"Brightness is now {level}%."


@tool(label="Volume")
def set_volume(percent: Percent = None, relative: Relative = False, muted: Annotated[bool, "true to mute, false to unmute"] = None):
    """Set the sound volume, mute or unmute, or leave everything out to hear what it is."""
    if muted is not None:
        system.set_muted(muted)
        if percent is None:
            return "Muted." if muted else "Unmuted."
    if percent is None:
        current, is_muted = system.get_volume()
        return f"Volume is {current}%{' and muted' if is_muted else ''}."
    current, is_muted = system.get_volume()
    level = target(current, percent, relative)
    system.set_volume(level)
    if is_muted and level > 0 and muted is None:
        system.set_muted(False)
    return f"Volume is now {level}%."


@tool(label="Keyboard light {percent}")
def set_keyboard_light(percent: Percent = None, relative: Relative = False):
    """Set the keyboard backlight brightness, or leave percent out to hear what it is."""
    if percent is None:
        return f"Keyboard light is {system.get_keyboard_light()}%."
    level = target(system.get_keyboard_light() if relative else 0, percent, relative)
    system.set_keyboard_light(level)
    return f"Keyboard light is now {level}%."


def playing_apps():
    """Apps sending sound to a speaker right now, read from macOS power assertions."""
    if sys.platform != "darwin":
        return None
    out = subprocess.run(["pmset", "-g", "assertions"], capture_output=True, text=True).stdout
    pids = set()
    for block in out.split("\n   pid ")[1:]:
        if "audio-out" in block:
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
        system.media_key(action)
        return f"Skipped to the {action} track."
    playing = playing_apps()
    if action == "pause" and playing == []:
        return "Nothing is playing, so there was nothing to pause."
    if action == "play" and playing:
        return f"{', '.join(playing)} is already playing."
    system.media_key("toggle")
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
        system.press("ctrl+cmd+q")
        return "Locked."
    if action == "sleep_display":
        subprocess.run(["pmset", "displaysleepnow"])
        return "Display is off."
    dark = "true" if action == "dark_mode" else "false"
    system.osascript(f'tell application "System Events" to tell appearance preferences to set dark mode to {dark}')
    return "Dark mode on." if dark == "true" else "Light mode on."
