"""THE TOOL. THE DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

import subprocess
from pathlib import Path

from langchain_core.tools import tool

from hands import reasons
from hands.shell.guard import report, shell

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
    else about the machine's settings, there are tools for those."""
    where = str(Path(directory).expanduser()) if directory else HOME

    if not Path(where).is_dir():
        return reasons.no(f"There is no folder at {where}.")

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
