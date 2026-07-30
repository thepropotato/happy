"""LOCKING, SLEEPING, SHUTTING DOWN, AND HOW MUCH BATTERY IS LEFT."""

from hands.controls.commands import (
    REFUSED,
    UNSUPPORTED,
    on_mac,
    on_windows,
    osascript,
    powershell,
    run,
)

# CONTROL COMMAND Q IS THE LOCK SHORTCUT ON EVERY MODERN MAC.
MAC_LOCK = 'tell application "System Events" to keystroke "q" using {command down, control down}'

WINDOWS_LOCK = ["rundll32.exe", "user32.dll,LockWorkStation"]
WINDOWS_SLEEP = ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"]

WINDOWS_BATTERY = (
    "Get-CimInstance Win32_Battery | ForEach-Object "
    '{ "$($_.EstimatedChargeRemaining) percent, status $($_.BatteryStatus)" }'
)

WINDOWS_STATES = {
    "1": "on battery",
    "2": "plugged in",
    "3": "fully charged",
    "4": "low",
    "5": "critical",
    "6": "charging",
    "7": "charging and high",
    "8": "charging and low",
    "9": "charging and critical",
}


def lock():
    if on_mac():
        done = osascript(MAC_LOCK)
    elif on_windows():
        done = run(WINDOWS_LOCK)
    else:
        return UNSUPPORTED

    return "Locked the screen." if done is not None else REFUSED


def sleep():
    if on_mac():
        done = run(["pmset", "sleepnow"])
    elif on_windows():
        done = run(WINDOWS_SLEEP)
    else:
        return UNSUPPORTED

    return "Going to sleep." if done is not None else REFUSED


def shut_down():
    if on_mac():
        done = osascript('tell application "System Events" to shut down')
    elif on_windows():
        done = run(["shutdown", "/s", "/t", "0"])
    else:
        return UNSUPPORTED

    return "Shutting down." if done is not None else REFUSED


def restart():
    if on_mac():
        done = osascript('tell application "System Events" to restart')
    elif on_windows():
        done = run(["shutdown", "/r", "/t", "0"])
    else:
        return UNSUPPORTED

    return "Restarting." if done is not None else REFUSED


def battery():
    if on_mac():
        said = run(["pmset", "-g", "batt"])

        return said or "I could not read the battery."

    if on_windows():
        said = powershell(WINDOWS_BATTERY)

        if not said:
            return "There is no battery in this computer, or I could not read it."

        return readable(said)

    return UNSUPPORTED


def readable(said):
    """WINDOWS ANSWERS WITH A NUMBER FOR THE STATE. SAY IT IN WORDS."""
    for code, meaning in WINDOWS_STATES.items():
        said = said.replace(f"status {code}", meaning)

    return said
