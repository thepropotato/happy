"""HANDING A PATH OR AN ADDRESS TO WHATEVER THE SYSTEM ALREADY USES FOR IT.

EVERY SYSTEM KNOWS WHICH PROGRAM OWNS A FILE AND WHICH BROWSER OWNS A LINK, AND
IT KNOWS BECAUSE THE PERSON TOLD IT ONCE. NOTHING HERE PICKS A BROWSER.
"""

import sys

from hands.apps import browsers
from hands.apps.running import launch, released

MACOS = "darwin"
WINDOWS = "win32"
LINUX = "linux"

MAC_OPEN = ["open"]
MAC_OPEN_APP = ["open", "-a"]
WINDOWS_OPEN = ["cmd", "/c", "start", ""]  # THE EMPTY STRING IS start'S TITLE SLOT.
LINUX_OPEN = ["xdg-open"]

# ANYTHING SAID OUT LOUD LIKE "youtube.com" IS AN ADDRESS WITH THE FRONT MISSING.
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

    if binary is None:  # SAFARI, FIREFOX, OR A PLATFORM WE CANNOT READ.
        how = opener()

        return launch(how + [address]) if how else UNSUPPORTED

    return released([str(binary), address])
