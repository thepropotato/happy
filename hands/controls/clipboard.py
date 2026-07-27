"""WHAT IS ON THE CLIPBOARD, AND PUTTING SOMETHING THERE."""

from pathlib import Path

from hands.controls.commands import (
    REFUSED,
    UNSUPPORTED,
    on_mac,
    on_windows,
    osascript,
    powershell,
    run,
)

# WHAT COMES BACK MAY BE SPOKEN, SO A COPIED PAGE MUST NOT ARRIVE WHOLE.
MAX_CHARS = 4000

EMPTY = "There is nothing on the clipboard."


def read():
    if on_mac():
        said = run(["pbpaste"])
    elif on_windows():
        said = powershell("Get-Clipboard -Raw")
    else:
        return UNSUPPORTED

    if not said:
        return EMPTY

    return said[:MAX_CHARS]


def write(text):
    if not text:
        return "There was nothing to copy."

    if on_mac():
        done = run(["pbcopy"], feed=text)
    elif on_windows():
        done = run(["clip"], feed=text)  # SHIPS WITH WINDOWS AND READS ITS INPUT.
    else:
        return UNSUPPORTED

    return "Copied it to the clipboard." if done is not None else REFUSED


def write_file(path):
    """PUT THE FILE ITSELF ON THE CLIPBOARD, THE WAY COPYING IT IN A FILE MANAGER
    DOES. THE COMPLAINT, OR None WHEN IT WORKED.

    A PATH WRITTEN AS TEXT PASTES AS TEXT. AN APPLICATION ONLY TREATS A PASTE AS
    AN ATTACHMENT WHEN WHAT IT FINDS IS A FILE.
    """
    where = Path(path).expanduser()

    if not where.is_file():
        return f"{where.name} is not a file I can copy."

    if on_mac():
        done = mac_file(where)
    elif on_windows():
        done = windows_file(where)
    else:
        return UNSUPPORTED

    return None if done else REFUSED


def mac_file(where):
    """THE PASTEBOARD DIRECTLY, WHICH LEAVES BOTH THE NAMES A MAC APPLICATION
    LOOKS FOR. THE SCRIPTING WAY LEAVES ONLY ONE OF THEM, SO IT IS THE FALLBACK."""
    try:
        from AppKit import NSURL, NSPasteboard
    except ImportError:
        return osascript(f'set the clipboard to POSIX file "{where.resolve()}"') is not None

    board = NSPasteboard.generalPasteboard()
    board.clearContents()

    return bool(board.writeObjects_([NSURL.fileURLWithPath_(str(where.resolve()))]))


def windows_file(where):
    quoted = str(where.resolve()).replace("'", "''")

    return powershell(f"Set-Clipboard -LiteralPath '{quoted}'") is not None
