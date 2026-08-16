"""HAPPY AS SOMETHING YOU CLICK: AN APP ON A MAC, A SHORTCUT ON WINDOWS, AN ENTRY ON LINUX.

Nothing is copied in. Each one points back at the folder Happy was installed into, so
updating him is a git pull and never a rebuild.
"""

import json
import plistlib
import shutil
from pathlib import Path

from bones import icons, packages, systems

NAME = "Happy"
IDENTIFIER = "com.thepropotato.happy"
VERSION = "1.0.0"

APPLICATIONS = Path("/Applications")
APP = APPLICATIONS / f"{NAME}.app"

WINDOW = packages.HAPPY / "face" / "window"

# WITHOUT A REASON WRITTEN DOWN FOR EACH ONE, MACOS KILLS THE APP THE MOMENT IT ASKS.
REASONS = {
    "NSMicrophoneUsageDescription":
        "Happy listens for his name and for what you ask him.",
    "NSCameraUsageDescription":
        "Happy does not use the camera.",
    "NSAppleEventsUsageDescription":
        "Happy opens and controls the apps you ask him to.",
    "NSSpeechRecognitionUsageDescription":
        "Happy works out what you said, on this machine.",
}

LINUX_ENTRY = """[Desktop Entry]
Type=Application
Name={name}
Comment=A completely local voice assistant
Exec={exec}
Icon={icon}
Terminal=false
Categories=Utility;
"""

# THE SHORTCUT IS MADE BY WINDOWS ITSELF, WHICH IS THE ONLY THING THAT WRITES A .lnk.
SHORTCUT = """
$link = (New-Object -ComObject WScript.Shell).CreateShortcut("{where}")
$link.TargetPath = "{target}"
$link.Arguments = '{arguments}'
$link.WorkingDirectory = "{working}"
$link.IconLocation = "{icon}"
$link.Description = "A completely local voice assistant"
$link.Save()
"""


def build():
    """THE ONE FOR THIS SYSTEM, OR A SENTENCE SAYING WHY THERE IS NONE."""
    if systems.on_mac():
        return mac()

    if systems.on_windows():
        return windows()

    return linux()


# ── MACOS ──

def mac():
    """ELECTRON'S OWN BUNDLE, RENAMED AND POINTED AT HAPPY."""
    source = packages.electron()

    if not source.is_dir():
        return None, "the window has no Electron yet"

    if not APPLICATIONS.is_dir():
        return None, "there is no /Applications on this machine"

    try:
        shutil.rmtree(APP, ignore_errors=True)
        shutil.copytree(source, APP, symlinks=True)
    except OSError as error:
        return None, f"could not write into /Applications ({error})"

    contents = APP / "Contents"

    rename(contents)
    dress(contents)
    point(contents)
    sign()

    return APP, ""


def rename(contents):
    """THE BINARY IS CALLED Electron AND EVERY REFERENCE TO IT HAS TO MOVE TOGETHER."""
    binaries = contents / "MacOS"
    (binaries / "Electron").rename(binaries / NAME)


def dress(contents):
    """THE NAME, THE ICON, AND THE REASONS THE SYSTEM WILL READ OUT IN ITS DIALOGS."""
    where = contents / "Info.plist"
    plist = plistlib.loads(where.read_bytes())

    plist.update(
        {
            "CFBundleName": NAME,
            "CFBundleDisplayName": NAME,
            "CFBundleExecutable": NAME,
            "CFBundleIdentifier": IDENTIFIER,
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "CFBundleIconFile": "happy",
            # HE LIVES IN THE MENU BAR, SO A DOCK ICON WOULD BE A SECOND WAY IN THAT
            # DOES NOTHING. index.js ALREADY HIDES IT AT RUNTIME.
            "LSUIElement": True,
            **REASONS,
        }
    )

    where.write_bytes(plistlib.dumps(plist))

    resources = contents / "Resources"

    for old in resources.glob("electron.icns"):
        old.unlink()

    icons.made(resources / "happy")


POINTER = """// THE APP IS TWO LINES POINTING AT THE REAL ONE, SO THERE IS ONLY EVER ONE COPY OF
// HAPPY AND UPDATING HIM IS A git pull RATHER THAN BUILDING THIS AGAIN.
require({where})
"""


def point(contents):
    """WHAT ELECTRON LOADS: A REAL FOLDER HOLDING ONE line THAT REACHES THE CHECKOUT.

    A symlink here would be the obvious way and cannot be used — codesign refuses to seal
    a bundle containing a link that leaves it, and an unsigned bundle will not launch at
    all. Requiring the absolute path leaves __dirname on the real file, so the window
    still finds the checkout three folders above it exactly as it always has.
    """
    where = contents / "Resources" / "app"

    if where.is_symlink():
        where.unlink()

    shutil.rmtree(where, ignore_errors=True)
    where.mkdir(parents=True)

    entry = WINDOW / "main" / "index.js"

    (where / "boot.js").write_text(POINTER.format(where=json.dumps(str(entry))), "utf-8")

    # THE NAME IS THE ONE THE REAL package.json CARRIES, BECAUSE ELECTRON KEEPS ITS
    # SETTINGS IN A FOLDER NAMED AFTER IT AND A NEW NAME WOULD LOSE THEM.
    (where / "package.json").write_text(
        json.dumps({"name": "happy-window", "version": VERSION, "main": "boot.js"}), "utf-8"
    )


# EVERY PIECE OF CODE IN THE BUNDLE, DEEPEST FIRST, WHICH IS THE ONLY ORDER THAT WORKS.
def sign():
    """AN AD HOC SIGNATURE, WHICH IS WHAT THE PERMISSIONS WILL BE REMEMBERED AGAINST.

    Renaming the binary and rewriting Info.plist both break the signature Electron came
    with, and macOS will not launch a bundle whose seal is broken. --deep looks like the
    answer and signs in the wrong order, so each nested piece is done by hand.
    """
    frameworks = APP / "Contents" / "Frameworks"

    for library in sorted(frameworks.rglob("*.dylib")):
        sealed(library)

    for nested in sorted(frameworks.glob("*.framework")):
        sealed(nested)

    for helper in sorted(frameworks.glob("*.app")):
        sealed(helper)

    sealed(APP / "Contents" / "MacOS" / NAME)

    return sealed(APP) and systems.run(["codesign", "--verify", "--strict", str(APP)])


def sealed(what):
    return systems.run(["codesign", "--force", "--sign", "-", str(what)])


# ── WINDOWS ──

def windows():
    where = menu() / f"{NAME}.lnk"

    # INTO data/, WHICH GIT ALREADY IGNORES: A BUILT ICON IS NOT SOMETHING TO COMMIT.
    made = packages.HAPPY / "data"
    made.mkdir(parents=True, exist_ok=True)

    icon = icons.made(made / "happy")

    if icon is None:
        return None, "the icon could not be made"

    where.parent.mkdir(parents=True, exist_ok=True)

    said = SHORTCUT.format(
        where=where,
        target=electron_exe(),
        arguments=".",
        working=WINDOW,
        icon=icon,
    )

    if not systems.run(["powershell", "-NoProfile", "-Command", said]):
        return None, "the shortcut would not be written"

    return where, ""


def menu():
    """WHERE WINDOWS KEEPS THE PROGRAMS SOMEBODY CAN SEARCH FOR."""
    import os

    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def electron_exe():
    return packages.electron()


# ── LINUX ──

def linux():
    where = Path.home() / ".local" / "share" / "applications" / f"{IDENTIFIER}.desktop"
    into = Path.home() / ".local" / "share" / "icons"

    into.mkdir(parents=True, exist_ok=True)
    where.parent.mkdir(parents=True, exist_ok=True)

    icon = icons.made(into / "happy")
    started = WINDOW / "node_modules" / ".bin" / "electron"

    where.write_text(
        LINUX_ENTRY.format(name=NAME, exec=f'"{started}" "{WINDOW}"', icon=icon),
        encoding="utf-8",
    )

    return where, ""
