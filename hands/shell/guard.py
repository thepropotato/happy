"""HOW A COMMAND IS HANDED TO A SHELL, AND WHAT COMES BACK WHEN IT RUNS."""

import re
import sys
from pathlib import Path

WINDOWS = "win32"

MAX_OUTPUT_CHARS = 4000
MIDDLE = "\n... [cut] ...\n"

# A STEER, NOT A WALL. THERE ARE ENDLESS WAYS TO SPELL A DELETE IN A SHELL AND THIS CATCHES
# ONE OF THEM, SO IT IS HERE TO TURN A MODEL THAT REACHED PAST move_to_trash BACK TOWARDS IT,
# NOT TO STOP A SHELL FROM BEING A SHELL. NOTHING DOWNSTREAM MAY ASSUME THIS CHECKED.
DELETERS = {"rm", "rmdir", "del", "erase", "unlink", "remove-item", "ri", "rd", "shred"}

# WHAT SEPARATES ONE COMMAND FROM THE NEXT, SO A DELETE HIDING BEHIND A cd IS STILL SEEN.
JOINS = ["&&", "||", "|", ";", "\n"]

SKIPPED = {"sudo", "doas", "time", "nohup", "command"}

INSTEAD = (
    "Deleting with a command cannot be undone. Use move_to_trash with the path, which puts "
    "it in the Trash where they can get it back."
)

# A SINGLE > ONTO A FILE THAT EXISTS REPLACES ALL OF IT WITHOUT ANYTHING HAVING READ IT. >>
# APPENDS, sed -i EDITS, git RESTORES: NONE OF THOSE ARE THIS, AND ALL OF THEM STAY OPEN.
REDIRECT = re.compile(r"(?<![>\d&])\s*>\s*(?!>|&)\s*([\"']?)([^\s\"'|;&]+)\1")

OVERWRITES = (
    "{path} already exists, and a > redirect would replace all of it unread. To change it, "
    "read it and use edit_file; to make something new, use write_file with a new name."
)


def clobbering(command, where):
    """THE EXISTING FILE A > REDIRECT IN THIS COMMAND WOULD WIPE, OR None."""
    for found in REDIRECT.finditer(command):
        target = Path(found.group(2)).expanduser()

        if not target.is_absolute():
            target = Path(where) / target

        if target.is_file():
            return target

    return None


def shell(command):
    """THE ARGV THAT RUNS command, WITHOUT HANDING IT TO A SECOND SHELL."""
    if sys.platform == WINDOWS:
        return ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]

    runner = "/bin/bash" if Path("/bin/bash").exists() else "/bin/sh"

    return [runner, "-c", command]


def deleting(command):
    """WHETHER THE COMMAND IS PLAINLY A DELETE, WHICH IS THE ONE ACT WITH A TOOL OF ITS OWN."""
    whole = command

    for join in JOINS:
        whole = whole.replace(join, ";")

    for piece in whole.split(";"):
        words = [word for word in piece.strip().split() if not word.startswith("-")]

        while words and words[0].lower() in SKIPPED:
            words = words[1:]

        # A PATH ENDING IN THE NAME IS STILL THE PROGRAM: /bin/rm AND rm ARE ONE THING.
        if words and words[0].rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower() in DELETERS:
            return True

    return False


def clip(text):
    if len(text) <= MAX_OUTPUT_CHARS:
        return text

    half = MAX_OUTPUT_CHARS // 2

    return text[:half] + MIDDLE + text[-half:]


def report(done):
    """WHAT IT PRINTED, LABELLED SO THE MODEL CAN TELL THE STREAMS APART."""
    parts = []

    if done.stdout and done.stdout.strip():
        parts.append(clip(done.stdout.strip()))

    if done.stderr and done.stderr.strip():
        parts.append("stderr:\n" + clip(done.stderr.strip()))

    if done.returncode != 0:
        parts.append(f"exit code {done.returncode}")

    return "\n\n".join(parts) if parts else "Done, it printed nothing."
