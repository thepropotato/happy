"""HOW A COMMAND IS HANDED TO A SHELL, AND WHAT COMES BACK WHEN IT RUNS."""

import sys
from pathlib import Path

WINDOWS = "win32"

MAX_OUTPUT_CHARS = 4000
MIDDLE = "\n... [cut] ...\n"


def shell(command):
    """THE ARGV THAT RUNS command, WITHOUT HANDING IT TO A SECOND SHELL."""
    if sys.platform == WINDOWS:
        return ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]

    runner = "/bin/bash" if Path("/bin/bash").exists() else "/bin/sh"

    return [runner, "-c", command]


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
