"""WHICH BROWSER OPENS LINKS HERE, AND WHETHER IT CAN BE DRIVEN.

`open` FINDS THE BROWSER ON ITS OWN AND IS ALWAYS THE BETTER ANSWER. THIS IS FOR
THE CALLER THAT HAS TO START A BROWSER ITSELF AND SO HAS TO BE TOLD WHICH ONE.
"""

import sys
from pathlib import Path

from hands.apps import chosen
from hands.apps.running import ask

MACOS = "darwin"
WINDOWS = "win32"
LINUX = "linux"

MAC_INFO = "Contents/Info.plist"
MAC_BINARIES = "Contents/MacOS"
MAC_FRAMEWORKS = "Contents/Frameworks"
MAC_ENGINE = "*Framework.framework"
MAC_EXECUTABLE_KEY = "CFBundleExecutable"

PLUTIL_RAW = ["plutil", "-extract"]

# CHROMIUM BROWSERS BY PROGRAM NAME, FOR THE TWO SYSTEMS WITH NO BUNDLE TO LOOK
# INSIDE. ON MACOS THIS IS NOT GUESSED: SEE engine().
CHROMIUM_NAMES = {
    "chrome",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "msedge",
    "microsoft-edge",
    "brave",
    "brave-browser",
    "opera",
    "opera_gx",
    "vivaldi",
}


def default_browser():
    """THE APP THAT OPENS LINKS, OR None IF NOBODY EVER SAID.

    None IS NOT A FAILURE. IT MEANS THE CHOICE WAS NEVER CHANGED.
    """
    if sys.platform == MACOS:
        return chosen.mac()

    if sys.platform == WINDOWS:
        return chosen.windows()

    return chosen.linux() if sys.platform.startswith(LINUX) else None


def drivable_browser():
    """THE DEFAULT BROWSER'S PROGRAM WHEN IT IS ONE THAT CAN BE DRIVEN, ELSE None.

    ONLY CHROMIUM BROWSERS SPEAK THE DEBUGGING PROTOCOL. SAFARI AND FIREFOX DO
    NOT, AND SAYING SO HERE BEATS LAUNCHING ONE AND WATCHING IT SIT THERE.
    """
    found = default_browser()

    return program(found) if found and engine(found) else None


def program(app):
    """THE THING TO ACTUALLY RUN, OUT OF WHATEVER THE PLATFORM CALLS AN APP."""
    if sys.platform != MACOS:
        return app

    named = ask(PLUTIL_RAW + [MAC_EXECUTABLE_KEY, "raw", str(app / MAC_INFO)])

    if not named:
        return None

    # NOT ALWAYS THE BUNDLE'S NAME: "Opera GX.app" RUNS A PROGRAM CALLED "Opera".
    binary = app / MAC_BINARIES / named.strip()

    return binary if binary.exists() else None


def engine(app):
    """WHETHER THIS BROWSER IS A CHROMIUM ONE."""
    if sys.platform == MACOS:
        # EVERY CHROMIUM BUNDLE SHIPS ITS ENGINE AS A FRAMEWORK BESIDE THE
        # PROGRAM, AND NOTHING ELSE DOES. A FACT ABOUT THE BUNDLE IN FRONT OF US
        # RATHER THAN A LIST OF BROWSERS WE HAVE HEARD OF.
        return any((Path(app) / MAC_FRAMEWORKS).glob(MAC_ENGINE))

    # NO BUNDLE TO LOOK INSIDE. IT FAILS BY SAYING NO, WHICH COSTS A FALLBACK.
    return Path(app).stem.lower() in CHROMIUM_NAMES
