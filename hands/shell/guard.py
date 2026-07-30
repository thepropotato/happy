"""WHAT A COMMAND WOULD DO, AND WHAT COMES BACK WHEN IT RUNS.

THE SHELL IS THE WIDEST TOOL HAPPY HAS. A MISHEARD WORD IS A DIFFERENT COMMAND,
SO ANYTHING THAT COULD NOT BE UNDONE GOES PAST A PERSON FIRST. THE CHECK IS A
LIST OF SHAPES, NOT A SANDBOX: IT CATCHES CARELESS, NOT HOSTILE.
"""

import re
import sys
from pathlib import Path

WINDOWS = "win32"

MAX_OUTPUT_CHARS = 4000
MIDDLE = "\n... [cut] ...\n"

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


def shell(command):
    """THE ARGV THAT RUNS command, WITHOUT HANDING IT TO A SECOND SHELL."""
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
