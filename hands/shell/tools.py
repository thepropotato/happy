"""THE TOOL. THE DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

import subprocess
from pathlib import Path

from langchain_core.tools import tool

from hands import reasons
from hands.shell.guard import INSTEAD, OVERWRITES, clobbering, deleting, report, shell

TIMEOUT_SECONDS = 30

# COMMANDS RUN FROM HOME, NOT FROM WHEREVER HAPPY WAS STARTED.
HOME = str(Path.home())


@tool
def run_command(command: str, directory: str = "") -> str:
    """Run one shell command on this computer and return what it printed. On
    macOS and Linux the shell is bash, on Windows it is PowerShell, so write the
    command for the right one. Optionally give a directory to run it in,
    otherwise it runs in the user's home folder.

    Use this for anything the other tools do not already cover: reading files,
    searching, checking what is running, moving things around. Do not use it to
    launch an app, open a folder, or change the volume, brightness, or anything
    else about the machine's settings, there are tools for those.

    Never delete anything with a command. rm, rmdir, del, Remove-Item and shred
    destroy the thing where it stands and nothing brings it back. Deleting is
    move_to_trash, which takes a path and puts it in the Trash where the person
    can get it back. That holds when move_to_trash has already refused: a refusal
    is the answer, not a reason to reach for a command instead.

    Never write a file with a command either. Creating one is write_file and
    changing one is edit_file; a > redirect onto a file that exists is refused
    here because it wipes the file unread.

    Anything about this person's own project runs in that project's folder:
    call file_in_front and pass the project it names as directory, because the
    home folder this starts in is never it and a git command in the wrong folder
    answers about a different thing.

    Never write a date or a time into a command: you are not told what day it
    is. Say when you mean in words the command works out itself, or get a real
    date from where_we_are."""
    if deleting(command):
        return reasons.no(INSTEAD)

    where = str(Path(directory).expanduser()) if directory else HOME

    if not Path(where).is_dir():
        return reasons.no(f"There is no folder at {where}.")

    wiped = clobbering(command, where)

    if wiped is not None:
        return reasons.no(OVERWRITES.format(path=wiped))

    try:
        done = subprocess.run(
            shell(command),
            cwd=where,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return reasons.no(f"It was still running after {TIMEOUT_SECONDS} seconds, so it was stopped.")
    except OSError as error:
        return reasons.no(f"Could not run it: {error}")

    return report(done)


TOOLS = [run_command]
