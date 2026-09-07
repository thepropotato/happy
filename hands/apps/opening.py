"""HANDING A PATH OR AN ADDRESS TO WHATEVER THE SYSTEM ALREADY USES FOR IT."""

import sys
import time

from hands.apps import browsers
from hands.apps.running import ask, launch, released

MACOS = "darwin"
WINDOWS = "win32"
LINUX = "linux"

# PLAIN, WITH NO FLAGS: MEASURED, THAT IS THE ONE THAT BRINGS THE APP TO THE FRONT. -F LEAVES
# IT BEHIND WHATEVER WAS THERE AND -g DELIBERATELY KEEPS IT BACK, SO NEITHER IS WANTED HERE.
MAC_OPEN = ["open"]
MAC_OPEN_APP = ["open", "-a"]

# `open -a` DOES NOT RELIABLY RAISE AN APP ALREADY RUNNING. ACTIVATE DOES.
MAC_ACTIVATE = 'tell application "{name}" to activate'

# HOW LONG AN APPLICATION GETS TO REACH THE FRONT.
FRONT_SECONDS = 8.0
FRONT_STEP = 0.2
WINDOWS_OPEN = ["cmd", "/c", "start", ""]  # THE EMPTY STRING IS start'S TITLE SLOT.
LINUX_OPEN = ["xdg-open"]

SCHEMES = ("http://", "https://")
SCHEME = "https://"

UNSUPPORTED = "Opening a web address is not supported on this platform."


def opener():
    """HOW THIS PLATFORM OPENS A PATH OR AN ADDRESS, OR None."""
    if sys.platform == MACOS:
        return MAC_OPEN

    if sys.platform == WINDOWS:
        return WINDOWS_OPEN

    return LINUX_OPEN if sys.platform.startswith(LINUX) else None


def app_opener():
    """HOW THIS PLATFORM OPENS AN APPLICATION BY NAME, OR None."""
    if sys.platform == MACOS:
        return MAC_OPEN_APP

    return WINDOWS_OPEN if sys.platform == WINDOWS else None


def path_in_app_opener(app):
    """HOW THIS PLATFORM OPENS A PATH INSIDE ONE NAMED APPLICATION, OR None."""
    if sys.platform == MACOS:
        return MAC_OPEN_APP + [app]

    return None


def answering(name, front):
    """TRUE WHEN WHAT IS IN FRONT IS THE APPLICATION WE ASKED FOR."""
    here, wanted = (front or "").strip().lower(), (name or "").strip().lower()

    return bool(here) and bool(wanted) and (here in wanted or wanted in here)


def raised(name, seconds=FRONT_SECONDS):
    """BRING AN APPLICATION TO THE FRONT AND WAIT UNTIL IT IS THERE."""
    from eyes.attention import front

    if sys.platform == MACOS:
        ask(["osascript", "-e", MAC_ACTIVATE.format(name=name)])

    ended = time.monotonic() + seconds

    while time.monotonic() < ended:
        if answering(name, front()[0]):
            return True

        time.sleep(FRONT_STEP)

    return answering(name, front()[0])


def web_address(said):
    """WHAT WAS SAID, AS SOMETHING A BROWSER WILL TAKE."""
    address = said.strip()

    if address.lower().startswith(SCHEMES):
        return address

    return SCHEME + address.lstrip("/")


def hand_over(address):
    """GIVE AN ADDRESS TO THE BROWSER THIS PERSON USES, IN THE PROFILE THEY USE."""
    binary = browsers.drivable_browser()

    if binary is None:
        how = opener()

        return launch(how + [address]) if how else UNSUPPORTED

    return released([str(binary), address])
