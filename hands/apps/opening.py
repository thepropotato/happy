"""HANDING A PATH OR AN ADDRESS TO WHATEVER THE SYSTEM ALREADY USES FOR IT.

EVERY SYSTEM KNOWS WHICH PROGRAM OWNS A FILE AND WHICH BROWSER OWNS A LINK, AND
IT KNOWS BECAUSE THE PERSON TOLD IT ONCE. NOTHING HERE PICKS A BROWSER.
"""

import sys
import time

from hands.apps import browsers
from hands.apps.running import ask, launch, released

MACOS = "darwin"
WINDOWS = "win32"
LINUX = "linux"

MAC_OPEN = ["open"]
MAC_OPEN_APP = ["open", "-a"]

# `open -a` LAUNCHES AN APPLICATION BUT DOES NOT RELIABLY RAISE ONE THAT IS
# ALREADY RUNNING. TELLING IT TO ACTIVATE IS WHAT BRINGS IT FORWARD.
MAC_ACTIVATE = 'tell application "{name}" to activate'

# HOW LONG AN APPLICATION GETS TO REACH THE FRONT. EVERYTHING AFTER THIS POINT
# IS READ OFF WHATEVER IS IN FRONT, SO A COLD START IS WORTH WAITING FOR.
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


def answering(name, front):
    """TRUE WHEN WHAT IS IN FRONT IS THE APPLICATION WE ASKED FOR.

    THE TWO NAMES ARE RARELY IDENTICAL. macOS CALLS VISUAL STUDIO CODE "Code",
    AND ON WINDOWS THE FRONT IS A WINDOW TITLE WITH A DOCUMENT'S NAME ON THE
    FRONT OF IT, SO EITHER CONTAINING THE OTHER IS THE TEST.
    """
    here, wanted = (front or "").strip().lower(), (name or "").strip().lower()

    return bool(here) and bool(wanted) and (here in wanted or wanted in here)


def raised(name, seconds=FRONT_SECONDS):
    """BRING AN APPLICATION TO THE FRONT AND WAIT UNTIL IT IS THERE.

    TRUE WHEN IT ARRIVED. NOTHING AFTER AN open_app IS WORTH READING UNTIL THIS
    IS TRUE: THE TREE, THE SCREENSHOT AND EVERY CLICK ALL GO TO WHATEVER IS
    ACTUALLY IN FRONT, WHICH IS HOW "OPEN WHATSAPP" ENDED UP CLICKING AROUND IN
    A BROWSER.
    """
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
    """WHAT WAS SAID, AS SOMETHING A BROWSER WILL TAKE. ANYTHING THAT IS NOT A
    PAGE COMES OUT AS A HARMLESS ONE RATHER THAN AS SOMETHING THE SYSTEM RUNS."""
    address = said.strip()

    if address.lower().startswith(SCHEMES):
        return address

    return SCHEME + address.lstrip("/")


def hand_over(address):
    """GIVE AN ADDRESS TO THE BROWSER THIS PERSON USES, IN THE PROFILE THEY USE.
    RETURNS THE COMPLAINT, OR None WHEN IT WORKED.

    THE SYSTEM'S OWN OPENER ADDRESSES AN APPLICATION RATHER THAN A PROFILE, SO
    IT HANDS THE LINK TO WHICHEVER COPY OF THAT BROWSER IS ALREADY RUNNING. A
    CHROMIUM STARTED WITHOUT A PROFILE FLAG USES THE ONE ITS OWNER BROWSES WITH,
    SO WHERE THE BROWSER IS KNOWN THE PROFILE IS SAID OUT LOUD.
    """
    binary = browsers.drivable_browser()

    if binary is None:
        how = opener()

        return launch(how + [address]) if how else UNSUPPORTED

    return released([str(binary), address])
