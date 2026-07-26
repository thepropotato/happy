"""
THE SHELL. ONE COMMAND IN, WHAT IT PRINTED BACK OUT.

THIS IS THE WIDEST TOOL HAPPY HAS, AND THE ONE HOLDING THE KNIFE. A MISHEARD
WORD IS A DIFFERENT COMMAND, SO ANYTHING THAT COULD NOT BE UNDONE GOES PAST A
PERSON FIRST. THE CHECK IS A LIST OF SHAPES, NOT A SANDBOX: IT CATCHES A MODEL
BEING CARELESS, NOT A MODEL BEING HOSTILE.

THE SHELL DIFFERS BY PLATFORM AND THE MODEL IS TOLD WHICH ONE IT IS TALKING TO,
BECAUSE BASH SPELLING SENT TO POWERSHELL FAILS IN CONFUSING WAYS.
"""

import re
import subprocess
import sys
from pathlib import Path

from langchain_core.tools import tool

WINDOWS = "win32"

TIMEOUT_SECONDS = 30

# WHAT COMES BACK GOES INTO A MODEL'S CONTEXT AND MAY THEN BE SPOKEN, SO A
# COMMAND THAT PRINTS A MEGABYTE MUST NOT COST A MEGABYTE.
MAX_OUTPUT_CHARS = 4000
MIDDLE = "\n... [cut] ...\n"

# COMMANDS RUN FROM HOME, NOT FROM WHEREVER HAPPY WAS STARTED. A PERSON SAYING
# "MY DOWNLOADS" MEANS THEIR OWN FILES, NOT THIS PROJECT'S FOLDER.
HOME = str(Path.home())

# SHAPES THAT HAVE TO BE ASKED ABOUT FIRST, WITH HOW TO SAY WHY OUT LOUD.
RISKY = [
    (r"\b(rm|rmdir|del|erase|remove-item)\b", "deletes files"),
    (r"\b(mkfs\w*|diskutil\s+erase\w*)\b|\bformat\s+[a-z]:", "erases a disk"),
    (r"\bdd\b[^|;&]*\bof=", "writes straight to a disk"),
    (r">\s*/dev/(sd|disk|nvme)", "writes straight to a disk"),
    (r"\b(sudo|doas|runas)\b", "runs as administrator"),
    (r"\|\s*(sh|bash|zsh|python\d?|iex|invoke-expression)\b", "runs code off the internet"),
    (r"\b(shutdown|reboot|halt|restart-computer|stop-computer)\b", "shuts the computer down"),
    (r"\b(kill|killall|pkill|taskkill|stop-process)\b", "kills running programs"),
    (r"\bchmod\b[^|;&]*\b777\b", "makes files writable by anyone"),
    (r"\breg\s+(delete|add)\b", "edits the registry"),
    (r"\b(crontab|schtasks|launchctl)\b", "schedules something to run later"),
    (r"\bgit\b[^|;&]*\bpush\b[^|;&]*\s(-f|--force)\b", "force pushes and can lose commits"),
    (r":\s*\(\s*\)\s*\{.*\}\s*;?\s*:", "is a fork bomb"),
]

CHECKS = [(re.compile(pattern, re.IGNORECASE), reason) for pattern, reason in RISKY]

YES = {"y", "yes", "yeah", "yep", "ok", "okay", "sure", "go ahead", "do it"}

REFUSED = "Cancelled, the user said no. Do not try to run it another way."


def shell(command):
    """THE ARGV THAT RUNS command, WITHOUT HANDING THE STRING TO A SECOND SHELL."""
    if sys.platform == WINDOWS:
        return ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]

    runner = "/bin/bash" if Path("/bin/bash").exists() else "/bin/sh"

    return [runner, "-c", command]


def danger(command):
    """WHY THIS NEEDS ASKING ABOUT, OR None WHEN IT DOES NOT."""
    for check, reason in CHECKS:
        if check.search(command):
            return reason

    return None


def console_confirm(command, reason):
    """THE DEFAULT WAY OF ASKING. A SPOKEN ONE CAN REPLACE IT THROUGH asks()."""
    print(f"\n  Happy wants to run a command that {reason}:\n    {command}")

    try:
        return input("  Allow it? [y/N] ").strip().lower() in YES
    except (EOFError, KeyboardInterrupt):
        print()
        return False


confirm = console_confirm


def asks(handler):
    """WIRE UP HOW HAPPY ASKS BEFORE RUNNING SOMETHING RISKY.

    handler(command, reason) -> bool. PASSING None PUTS THE CONSOLE BACK.
    """
    global confirm

    confirm = handler or console_confirm


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


# TOOLS. THE DESCRIPTION BELOW IS READ BY THE MODEL, NOT BY US, SO IT IS
# WRITTEN AS PLAIN PROSE RATHER THAN AS A COMMENT.


@tool
def run_command(command: str, directory: str = "") -> str:
    """Run one shell command on this computer and return what it printed. On
    macOS and Linux the shell is bash, on Windows it is PowerShell, so write the
    command for the right one. Optionally give a directory to run it in,
    otherwise it runs in the user's home folder.

    Use this for anything the other tools do not already cover: reading files,
    searching, checking what is running, moving things around. Do not use it to
    launch an app or to open a folder, there are tools for those. Anything that
    deletes or overwrites is shown to the user for approval first, so prefer a
    command that reports over one that changes."""
    reason = danger(command)

    if reason and not confirm(command, reason):
        return REFUSED

    where = str(Path(directory).expanduser()) if directory else HOME

    if not Path(where).is_dir():
        return f"There is no folder at {where}."

    try:
        done = subprocess.run(
            shell(command),
            cwd=where,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return f"It was still running after {TIMEOUT_SECONDS} seconds, so it was stopped."
    except OSError as error:
        return f"Could not run it: {error}"

    return report(done)


TOOLS = [run_command]


if __name__ == "__main__":
    print(run_command.invoke({"command": "echo hello && pwd"}))
