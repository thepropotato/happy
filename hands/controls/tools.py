"""THE TOOLS."""

from langchain_core.tools import tool

from hands import reasons
from hands.controls import clipboard, display, keyboard, media, network, power, volume

STEP = 10  # HOW MUCH "A BIT LOUDER" IS WORTH.

UP = "up"
DOWN = "down"


@tool
def sound_control(action: str, level: int = -1) -> str:
    """Control the sound on this computer. Actions: "status" to say what the
    volume is, "set" with a level from 0 to 100, "up" or "down" to step it by
    ten (or by level if you give one), "mute" and "unmute".

    Use this for anything about volume or sound being on or off, for example
    "turn it down", "set the volume to thirty", "mute that"."""
    wanted = (action or "").strip().lower()
    step = STEP if level < 0 else level

    if wanted == "status":
        return volume.status()

    if wanted == "set":
        return volume.set_level(level)

    if wanted == UP:
        return volume.change(step)

    if wanted == DOWN:
        return volume.change(-step)

    if wanted in ("mute", "unmute"):
        return volume.mute(wanted == "mute")

    return reasons.no(f"I can set, step, mute or report the volume, not {action}.")


@tool
def brightness_control(action: str, level: int = -1) -> str:
    """Control the brightness of the screen. Actions: "status" to say what it is,
    "set" with a level from 0 to 100, "up" or "down" to step it by ten (or by
    level if you give one).

    Use this for "make the screen brighter", "dim the screen", "set brightness
    to fifty". This is the built in screen; an external monitor has its own
    buttons and cannot always be asked.

    This is the screen and only the screen. The light under the keys is a
    different thing on a different tool: anything about the keyboard, its keys or
    its backlight goes to keyboard_backlight, never here. Setting this to nought
    blacks out their display, which is not what somebody asking about their
    keyboard wanted."""
    wanted = (action or "").strip().lower()
    step = STEP if level < 0 else level

    if wanted == "status":
        return display.status()

    if wanted == "set":
        return display.set_level(level)

    if wanted == UP:
        return display.change(step)

    if wanted == DOWN:
        return display.change(-step)

    return reasons.no(f"I can set, step or report the brightness, not {action}.")


@tool
def keyboard_backlight(action: str, level: int = -1) -> str:
    """Control the light under the keys of the keyboard. Actions: "status" to say
    what it is, "set" with a level from 0 to 100, "up" or "down" to step it by ten
    (or by level if you give one).

    Use this for "turn the keyboard backlight off", "light my keys up", "dim the
    keyboard". This is the keyboard, not the screen: to change what they are
    looking at use brightness_control instead.

    Only a built in Mac keyboard answers this. Anywhere else, and on an external
    keyboard, it says so rather than changing anything, and that answer is the one
    to pass on: say the keys on the keyboard do it, and do not reach for the screen
    instead."""
    wanted = (action or "").strip().lower()
    step = STEP if level < 0 else level

    if wanted == "status":
        return keyboard.status()

    if wanted == "set":
        return keyboard.set_level(level)

    if wanted == UP:
        return keyboard.change(step)

    if wanted == DOWN:
        return keyboard.change(-step)

    return reasons.no(f"I can set, step or report the keyboard backlight, not {action}.")


@tool
def media_control(action: str) -> str:
    """Control whatever is playing music or video: "play", "pause", "next" or
    "previous". Use this for "pause the music", "skip this song", "play it
    again"."""
    return media.control(action)


@tool
def display_control(action: str) -> str:
    """Control the display itself. Actions: "off" to put the screen to sleep
    without locking anything, "dark" and "light" to switch the system appearance.

    Use "off" for "turn the screen off", and dark or light for "switch to dark
    mode". To lock the computer use power_control instead."""
    wanted = (action or "").strip().lower()

    if wanted == "off":
        return display.off()

    if wanted in ("dark", "light"):
        return display.dark_mode(wanted == "dark")

    return reasons.no(f"I can turn the screen off or switch dark mode, not {action}.")


@tool
def power_control(action: str) -> str:
    """Lock, sleep, restart or shut the computer down, or report the battery.
    Actions: "battery", "lock", "sleep", "restart", "shutdown".

    Sleeping, restarting and shutting down take anything unsaved with them, so
    say what is about to happen before doing one."""
    wanted = (action or "").strip().lower()

    if wanted == "battery":
        return power.battery()

    if wanted == "lock":
        return power.lock()

    act = {
        "sleep": power.sleep,
        "restart": power.restart,
        "shutdown": power.shut_down,
    }.get(wanted)

    if act is None:
        return reasons.no(f"I can report the battery, lock, sleep, restart or shut down, not {action}.")

    return act()


@tool
def network_control(action: str) -> str:
    """Report or switch the Wi-Fi. Actions: "status" to say whether it is on and
    which network it is joined to, "on" and "off" to switch the adapter.

    Use this for "am I online", "what wifi am I on", "turn the wifi off"."""
    wanted = (action or "").strip().lower()

    if wanted == "status":
        return network.status()

    if wanted in ("on", "off"):
        return network.switch(wanted == "on")

    return reasons.no(f"I can report or switch the Wi-Fi, not {action}.")


@tool
def clipboard_control(action: str, text: str = "") -> str:
    """Read the clipboard or put something on it. Actions: "read" to say what is
    on it, "write" with text to copy that text.

    Use this for "what did I just copy", "copy that down", "put this on my
    clipboard"."""
    wanted = (action or "").strip().lower()

    if wanted == "read":
        return clipboard.read()

    if wanted == "write":
        return clipboard.write(text)

    return reasons.no(f"I can read the clipboard or write to it, not {action}.")


TOOLS = [
    sound_control,
    brightness_control,
    keyboard_backlight,
    media_control,
    display_control,
    power_control,
    network_control,
    clipboard_control,
]
