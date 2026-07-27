"""THE WI-FI: WHETHER IT IS ON, WHAT IT IS ON, AND TURNING IT OVER."""

from hands.controls.commands import (
    REFUSED,
    UNSUPPORTED,
    on_mac,
    on_windows,
    powershell,
    run,
)

WIFI_PORT = "Wi-Fi"

WINDOWS_ADAPTER = (
    "Get-NetAdapter | Where-Object { $_.Name -like '*Wi-Fi*' -or "
    "$_.InterfaceDescription -like '*Wireless*' } | Select-Object -First 1 -ExpandProperty Name"
)
WINDOWS_STATUS = "netsh wlan show interfaces"
WINDOWS_SWITCH = "{verb}-NetAdapter -Name '{name}' -Confirm:$false"

NO_ADAPTER = "I could not find a Wi-Fi adapter on this computer."

# TURNING AN ADAPTER OFF IS AN ADMINISTRATOR'S JOB ON WINDOWS.
NEEDS_RIGHTS = "Windows would not let me switch the Wi-Fi adapter without administrator rights."


def mac_device():
    """THE INTERFACE THE WI-FI LIVES ON, WHICH IS NOT ALWAYS en0."""
    lines = (run(["networksetup", "-listallhardwareports"]) or "").splitlines()

    for index, line in enumerate(lines):
        if WIFI_PORT in line and index + 1 < len(lines):
            return lines[index + 1].split(":")[-1].strip()

    return None


def windows_adapter():
    return (powershell(WINDOWS_ADAPTER) or "").strip() or None


def status():
    if on_mac():
        device = mac_device()

        if device is None:
            return NO_ADAPTER

        power = run(["networksetup", "-getairportpower", device]) or ""

        if "Off" in power:
            return "Wi-Fi is off."

        network = run(["networksetup", "-getairportnetwork", device]) or ""

        return f"Wi-Fi is on. {network.strip()}"

    if on_windows():
        said = powershell(WINDOWS_STATUS)

        return said or "Wi-Fi is off, or there is no wireless adapter."

    return UNSUPPORTED


def switch(on):
    if on_mac():
        device = mac_device()

        if device is None:
            return NO_ADAPTER

        done = run(["networksetup", "-setairportpower", device, "on" if on else "off"])
    elif on_windows():
        name = windows_adapter()

        if name is None:
            return NO_ADAPTER

        done = powershell(WINDOWS_SWITCH.format(verb="Enable" if on else "Disable", name=name))

        if done is None:
            return NEEDS_RIGHTS
    else:
        return UNSUPPORTED

    if done is None:
        return REFUSED

    return "Wi-Fi on." if on else "Wi-Fi off."
