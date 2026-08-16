"""WHICH MACHINE THIS IS, AND HOW IT INSTALLS THINGS."""

import os
import shutil
import subprocess
import sys

MACOS = "darwin"
WINDOWS = "win32"

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
