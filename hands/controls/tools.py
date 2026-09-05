"""THE TOOLS."""

from langchain_core.tools import tool

from hands import reasons
from hands.controls import clipboard, display, keyboard, media, network, power, volume

STEP = 10  # HOW MUCH "A BIT LOUDER" IS WORTH.

UP = "up"
DOWN = "down"


@tool
def system_control(part: str, action: str, level: int = -1, text: str = "") -> str:
    """Everything about this computer's own settings: sound, screen, keys, power,
    Wi-Fi, the clipboard and whatever is playing.

    part, then the action it takes:
    "volume": status, set (level 0-100), up, down, mute, unmute.
    "brightness": status, set (level 0-100), up, down. The screen itself.
    "keyboard": status, set (level 0-100), up, down. The light under the keys,
    which is a different thing from the screen; a Mac laptop only.
    "media": play, pause, next, previous. Whatever is playing music or video.
    "screen": off to put it to sleep without locking, dark or light for the
    system appearance.
    "power": battery, lock, sleep, restart, shutdown. The last three take
    anything unsaved with them, so say what is about to happen first.
    "wifi": status, on, off.
    "clipboard": read, or write with text.

    level is only for volume, brightness and keyboard; text is only for the
    clipboard write."""
    where = (part or "").strip().lower()
    wanted = (action or "").strip().lower()

    if where == "volume":
        return sound(wanted, action, level)

    if where == "brightness":
        return brightness(wanted, action, level)

    if where == "keyboard":
        return backlight(wanted, action, level)

    if where == "media":
        return media.control(action)

    if where == "screen":
        return screen(wanted, action)

    if where == "power":
        return powered(wanted, action)

    if where == "wifi":
        return wifi(wanted, action)

    if where == "clipboard":
        return copied(wanted, action, text)

    return reasons.no(
        f"I can work the volume, brightness, keyboard light, media, screen, power, "
        f"wifi or clipboard, not {part}."
    )


def sound(wanted, said, level):
    """VOLUME: REPORT IT, SET IT, STEP IT, OR SILENCE IT."""
    if wanted == "status":
        return volume.status()

    if wanted == "set":
        return volume.set_level(level)

    if wanted in (UP, DOWN):
        return volume.change(stepped(level, wanted))

    if wanted in ("mute", "unmute"):
        return volume.mute(wanted == "mute")

    return reasons.no(f"I can set, step, mute or report the volume, not {said}.")


def brightness(wanted, said, level):
    """THE SCREEN'S OWN BRIGHTNESS, WHICH IS NEVER THE LIGHT UNDER THE KEYS."""
    if wanted == "status":
        return display.status()

    if wanted == "set":
        return display.set_level(level)

    if wanted in (UP, DOWN):
        return display.change(stepped(level, wanted))

    return reasons.no(f"I can set, step or report the brightness, not {said}.")


def backlight(wanted, said, level):
    """THE LIGHT UNDER THE KEYS. A BUILT IN MAC KEYBOARD ONLY, AND IT SAYS SO ITSELF."""
    if wanted == "status":
        return keyboard.status()

    if wanted == "set":
        return keyboard.set_level(level)

    if wanted in (UP, DOWN):
        return keyboard.change(stepped(level, wanted))

    return reasons.no(f"I can set, step or report the keyboard backlight, not {said}.")


def screen(wanted, said):
    """THE DISPLAY ITSELF: ASLEEP, OR DRESSED DARK OR LIGHT."""
    if wanted == "off":
        return display.off()

    if wanted in ("dark", "light"):
        return display.dark_mode(wanted == "dark")

    return reasons.no(f"I can turn the screen off or switch dark mode, not {said}.")


def powered(wanted, said):
    """THE BATTERY, THE LOCK, AND THE THREE THAT TAKE UNSAVED WORK WITH THEM."""
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
        return reasons.no(
            f"I can report the battery, lock, sleep, restart or shut down, not {said}."
        )

    return act()


def wifi(wanted, said):
    if wanted == "status":
        return network.status()

    if wanted in ("on", "off"):
        return network.switch(wanted == "on")

    return reasons.no(f"I can report or switch the Wi-Fi, not {said}.")


def copied(wanted, said, text):
    if wanted == "read":
        return clipboard.read()

    if wanted == "write":
        return clipboard.write(text)

    return reasons.no(f"I can read the clipboard or write to it, not {said}.")


def stepped(level, wanted):
    """HOW FAR ONE "UP" OR "DOWN" MOVES, AND WHICH WAY."""
    step = STEP if level < 0 else level

    return step if wanted == UP else -step


TOOLS = [system_control]
