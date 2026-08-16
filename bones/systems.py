"""WHICH MACHINE THIS IS, WHAT IT HAS ON ITS PATH, AND HOW IT INSTALLS THINGS."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

MACOS = "darwin"
WINDOWS = "win32"

# WHAT A MAC CALLS THE COUNT OF ITS FAST CORES. AN INTEL ONE HAS NO SUCH SPLIT AND NO SUCH KEY.
FAST_CORES = "hw.perflevel0.logicalcpu"

# WHAT EACH SYSTEM INSTALLS WITH, IN THE ORDER WE WOULD RATHER USE THEM.
MANAGERS = {
    MACOS: [("brew", ["brew", "install"])],
    WINDOWS: [("winget", ["winget", "install", "--silent", "--accept-package-agreements",
                          "--accept-source-agreements", "-e", "--id"])],
}

LINUX = [
    ("apt-get", ["sudo", "apt-get", "install", "-y"]),
    ("dnf", ["sudo", "dnf", "install", "-y"]),
    ("pacman", ["sudo", "pacman", "-S", "--noconfirm"]),
    ("zypper", ["sudo", "zypper", "install", "-y"]),
]

# HOMEBREW IS THE ONE THING ON A MAC THAT NOTHING ELSE CAN INSTALL FOR US.
BREW = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'

NO_MANAGER = {
    MACOS: f"Happy installs things with Homebrew, which is not here. Get it with:\n    {BREW}",
    WINDOWS: "Happy installs things with winget, which is not here. It comes with App Installer "
             "from the Microsoft Store.",
}

NO_MANAGER_LINUX = "No apt, dnf, pacman or zypper here, so nothing can be installed for you."


def on_mac():
    return sys.platform == MACOS


def on_windows():
    return sys.platform == WINDOWS


def cores():
    """HOW MANY CORES TO RUN A MODEL ON: THE FAST ONES WHERE THE MACHINE TELLS THEM APART, AND
    ALL OF THEM WHERE THEY ARE ALL ALIKE.

    A MAC'S SLOW CORES COUNT AS CORES AND ARE THEN HANDED AN EQUAL SHARE OF EVERY BATCH THE
    FAST ONES HAVE TO WAIT ON, SO A SESSION GIVEN ALL TWELVE RUNS AT A THIRD OF THE SPEED OF
    ONE GIVEN THE EIGHT THAT CAN KEEP UP, AND IS ERRATIC WITH IT."""
    if on_mac():
        counted = output(["sysctl", "-n", FAST_CORES])

        if counted.isdigit():
            return int(counted)

    return os.cpu_count() or 1


def manager():
    """THE NAME AND THE INSTALL COMMAND FOR THIS MACHINE, OR None WHERE THERE IS NEITHER."""
    for name, command in MANAGERS.get(sys.platform, LINUX):
        if shutil.which(name):
            return name, command

    return None


def cannot_install():
    return NO_MANAGER.get(sys.platform, NO_MANAGER_LINUX)


def found(program):
    """WHERE A PROGRAM IS, LOOKING PAST A PATH THAT AN INSTALLER NEVER ADDED TO."""
    where = shutil.which(program)

    if where:
        return where

    for guess in GUESSES.get(sys.platform, []):
        path = os.path.expandvars(guess.format(program=program))

        if os.path.exists(path):
            return path

    return None


# THE PLACES AN INSTALLER PUTS THINGS WITHOUT TELLING THE SHELL ABOUT THEM.
GUESSES = {
    MACOS: ["/opt/homebrew/bin/{program}", "/usr/local/bin/{program}"],
    WINDOWS: [
        r"%LOCALAPPDATA%\Programs\{program}\{program}.exe",
        r"%PROGRAMFILES%\{program}\{program}.exe",
    ],
}


def run(command, quiet=True, timeout=None):
    """TRUE WHERE IT CAME BACK HAPPY. NOTHING IS EVER RUN THROUGH A SHELL."""
    try:
        finished = subprocess.run(
            command,
            stdout=subprocess.DEVNULL if quiet else None,
            stderr=subprocess.STDOUT if quiet else None,
            timeout=timeout,
            check=False,
        )

        return finished.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def output(command, timeout=15):
    """WHAT IT PRINTED, OR AN EMPTY STRING WHERE IT WOULD NOT RUN."""
    try:
        finished = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False
        )

        return (finished.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def install(package):
    """HAND ONE PACKAGE NAME TO WHATEVER THIS MACHINE INSTALLS WITH."""
    picked = manager()

    if not picked:
        return False

    return run([*picked[1], package], quiet=False)


# AN rc FILE THAT PRINTS A BANNER PRINTS IT BEFORE THIS, SO THE PATH IS WHATEVER FOLLOWS.
MARK = "<<happy>>"

# THE FOLDERS AN INSTALLER WRITES INTO WITHOUT TELLING ANY SHELL, FOR WHEN THE SHELL WILL NOT SAY.
BINS = {
    MACOS: ["/opt/homebrew/bin", "/usr/local/bin", "~/.local/bin", "~/bin", "~/.bun/bin",
            "~/.cargo/bin", "~/.volta/bin", "~/.npm-global/bin"],
    WINDOWS: [r"%APPDATA%\npm", r"%LOCALAPPDATA%\Microsoft\WindowsApps",
              r"%USERPROFILE%\.local\bin", r"%USERPROFILE%\.bun\bin", r"%USERPROFILE%\.cargo\bin"],
}

BINS_LINUX = ["~/.local/bin", "~/bin", "/usr/local/bin", "/home/linuxbrew/.linuxbrew/bin",
              "~/.bun/bin", "~/.cargo/bin", "~/.volta/bin", "~/.npm-global/bin"]

healed = False


def heal():
    """THE PATH WIDENED TO THE ONE A PERSON INSTALLS INTO. CLICKED FROM THE DOCK HE HAS FOUR
    SYSTEM FOLDERS AND NOTHING ELSE, SO EVERY CODER AND TOOL THEY HAVE IS INVISIBLE."""
    global healed

    if healed:
        return os.environ["PATH"]

    healed = True
    given = (os.environ.get("PATH") or "").split(os.pathsep)
    os.environ["PATH"] = os.pathsep.join(once([*given, *login(), *BINS.get(sys.platform, BINS_LINUX)]))

    return os.environ["PATH"]


def login():
    """WHAT A LOGIN SHELL SAYS ITS PATH IS, BECAUSE THAT IS THE ONE A PERSON ACTUALLY USES."""
    if on_windows():  # NO LOGIN SHELL DECIDES IT THERE, THE REGISTRY DOES.
        return []

    shell = os.environ.get("SHELL") or "/bin/sh"
    said = output([shell, "-lc", f'printf "%s%s" "{MARK}" "$PATH"'], timeout=5)

    return said.rsplit(MARK, 1)[1].split(os.pathsep) if MARK in said else []


def once(folders):
    """EACH REAL FOLDER ONE TIME, IN THE ORDER IT WAS FIRST NAMED."""
    seen, order = set(), []

    for folder in folders:
        full = str(Path(os.path.expandvars(folder.strip())).expanduser())

        if not folder.strip() or full in seen or not os.path.isdir(full):
            continue

        seen.add(full)
        order.append(full)

    return order
