"""THE BRIGHTNESS, THE DISPLAY, AND WHICH WAY ROUND THE COLOURS GO."""

import re
import shutil

from hands.controls import backlight
from hands.controls.commands import (
    REFUSED,
    UNSUPPORTED,
    clamp,
    number,
    on_mac,
    on_windows,
    osascript,
    powershell,
    run,
)

# THREE WAYS OF SETTING A MAC'S BRIGHTNESS, BEST FIRST: THE FRAMEWORK THE SLIDER
# ITSELF USES, THE HOMEBREW HELPER FOR THE OLD MACS THAT STILL ANSWER IT, AND
# THE KEYS, WHICH ALWAYS WORK BUT ONLY MOVE IN NOTCHES.
HELPER = "brightness"
HELPER_INSTALL = "brew install brightness"

BRIGHTER = 144
DIMMER = 145

# ONE NOTCH OF THE BRIGHTNESS KEY IS ABOUT A SIXTEENTH OF THE RANGE.
NOTCH = 100 / 16

MAC_LEVEL = re.compile(r"brightness\s+([0-9.]+)")

# WMI KNOWS THE BRIGHTNESS OF A BUILT IN SCREEN. AN EXTERNAL MONITOR IS ITS OWN
# DEVICE WITH ITS OWN BUTTONS AND DOES NOT ANSWER.
WINDOWS_READ = "(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness).CurrentBrightness"
WINDOWS_SET = (
    "(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods)"
    ".WmiSetBrightness(1, {level})"
)

# TELLING EVERY WINDOW THE SCREEN IS GOING TO SLEEP, WHICH IS WHAT THE POWER
# BUTTON DOES.
WINDOWS_DISPLAY_OFF = (
    '(Add-Type -MemberDefinition \'[DllImport("user32.dll")] public static extern int '
    "SendMessage(int handle, int message, int first, int second);' -Name Screen -PassThru)"
    "::SendMessage(-1, 0x0112, 0xF170, 2)"
)

WINDOWS_THEME = (
    r"Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize' "
    "-Name {name} -Value {value}"
)

NO_HELPER = (
    "I could not set an exact brightness on this Mac, so I have stepped it instead. "
    f"For an exact level you can install the helper with: {HELPER_INSTALL}"
)


def helper():
    return shutil.which(HELPER)


def mac_level():
    """THE BRIGHTNESS AS A PERCENTAGE, OR None. THE FRAMEWORK FIRST, THEN THE
    HELPER FOR THE MACS THAT PREDATE IT ANSWERING."""
    fraction = backlight.level()

    if fraction is not None:
        return round(fraction * 100)

    found = helper()

    if not found:
        return None

    said = MAC_LEVEL.search(run([found, "-l"]) or "")

    return round(float(said.group(1)) * 100) if said else None


def status():
    if on_mac():
        level = mac_level()

        if level is None:
            return "I could not read the brightness on this Mac."

        return f"The screen brightness is {level} percent."

    if on_windows():
        level = number(powershell(WINDOWS_READ))

        if level is None:
            return "I could not read the brightness. An external monitor cannot be asked."

        return f"The screen brightness is {level} percent."

    return UNSUPPORTED


def set_level(wanted):
    value = clamp(wanted)

    if value is None:
        return "The brightness has to be a number between zero and one hundred."

    if on_mac():
        if backlight.put(value / 100):
            return f"Brightness set to {value} percent."

        found = helper()

        if not found:
            # THE KEYS CANNOT NAME A LEVEL, BUT THEY CAN CLOSE THE GAP TO ONE,
            # WHICH IS NEARER TO WHAT WAS ASKED FOR THAN DOING NOTHING AND
            # RECOMMENDING HOMEBREW.
            now = mac_level()

            return NO_HELPER if now is None else f"{change(value - now)} {NO_HELPER}"

        done = run([found, str(value / 100)])
    elif on_windows():
        done = powershell(WINDOWS_SET.format(level=value))
    else:
        return UNSUPPORTED

    return f"Brightness set to {value} percent." if done is not None else REFUSED


def change(step):
    if on_mac():
        now = mac_level()

        # STEPPING IS SET_LEVEL WITH ONE EXTRA READ WHENEVER THE FRAMEWORK IS
        # THERE. THE KEYS BELOW ARE FOR WHEN IT IS NOT, AND THEY ARE DELIBERATELY
        # NOT REACHED THROUGH set_level, WHICH FALLS BACK TO HERE.
        if now is not None and backlight.put(clamp(now + step) / 100):
            return f"Brightness set to {clamp(now + step)} percent."

        for _ in range(max(1, round(abs(step) / NOTCH))):
            if osascript(f'tell application "System Events" to key code {BRIGHTER if step > 0 else DIMMER}') is None:
                return "I could not reach the brightness keys."
    elif on_windows():
        now = number(powershell(WINDOWS_READ))

        if now is None:
            return "I could not read the brightness."

        return set_level(now + step)
    else:
        return UNSUPPORTED

    return "Brightness turned up." if step > 0 else "Brightness turned down."


def display_off():
    if on_mac():
        done = run(["pmset", "displaysleepnow"])
    elif on_windows():
        done = powershell(WINDOWS_DISPLAY_OFF)
    else:
        return UNSUPPORTED

    return "Screen off." if done is not None else REFUSED


def dark_mode(on):
    if on_mac():
        done = osascript(
            "tell application \"System Events\" to tell appearance preferences to "
            f"set dark mode to {'true' if on else 'false'}"
        )
    elif on_windows():
        value = 0 if on else 1
        apps = powershell(WINDOWS_THEME.format(name="AppsUseLightTheme", value=value))
        done = powershell(WINDOWS_THEME.format(name="SystemUsesLightTheme", value=value))
        done = done if apps is not None else None
    else:
        return UNSUPPORTED

    if done is None:
        return REFUSED

    return "Dark mode on." if on else "Dark mode off."
