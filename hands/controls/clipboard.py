"""WHAT IS ON THE CLIPBOARD, AND PUTTING SOMETHING THERE."""

import time
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

# NOTHING A PERSON WOULD GENUINELY HAVE ON THEIR CLIPBOARD, SO A COPY THAT DID NOTHING
# — NOTHING WAS HIGHLIGHTED — IS TOLD APART FROM ONE THAT HONESTLY COPIED THIS EXACT TEXT.
SENTINEL = "\x00 happy is checking for a selection \x00"

NOTHING_SELECTED = "Nothing looks selected right now."

# HOW LONG TO GIVE THE COPY SHORTCUT TO ACTUALLY REACH THE CLIPBOARD BEFORE READING IT BACK.
SETTLE_SECONDS = 0.2


def raw():
    """WHAT IS ACTUALLY ON THE CLIPBOARD, OR None IF IT IS EMPTY OR CANNOT BE READ."""
    if on_mac():
        said = run(["pbpaste"])
    elif on_windows():
        said = powershell("Get-Clipboard -Raw")
    else:
        return None

    return said or None


def read():
    said = raw()

    return said[:MAX_CHARS] if said else EMPTY


def write(text):
    if not text:
        return "There was nothing to copy."

    if on_mac():
        done = run(["pbcopy"], feed=text)
    elif on_windows():
        done = run(["clip"], feed=text)
    else:
        return UNSUPPORTED

    return "Copied it to the clipboard." if done is not None else REFUSED


def clear():
    """EMPTY THE CLIPBOARD OUTRIGHT. write() REFUSES EMPTY TEXT, SO THIS GOES STRAIGHT
    TO THE PLATFORM COMMAND INSTEAD, FOR THE ONE CASE WHERE EMPTY IS THE POINT."""
    if on_mac():
        run(["pbcopy"], feed="")
    elif on_windows():
        run(["clip"], feed="")


def selection():
    """WHATEVER TEXT IS HIGHLIGHTED IN WHICHEVER WINDOW HAS FOCUS RIGHT NOW, OR None IF
    NOTHING IS. COPIES IT TO CHECK, THEN PUTS BACK WHATEVER WAS ON THE CLIPBOARD BEFORE,
    SO ASKING WHAT SOMETHING SAYS NEVER QUIETLY THROWS AWAY WHAT THEY HAD COPIED."""
    if not (on_mac() or on_windows()):
        return None

    from hands.desktop import pointer  # LATE: hands.desktop REACHES BACK INTO eyes.

    before = raw()

    write(SENTINEL)

    complaint = pointer.press("cmd+c" if on_mac() else "ctrl+c")

    time.sleep(SETTLE_SECONDS)

    after = raw()

    if before is None:
        clear()
    else:
        write(before)

    if complaint or after is None or after == SENTINEL:
        return None

    return after[:MAX_CHARS]


def write_file(path):
    """PUT THE FILE ITSELF ON THE CLIPBOARD, THE WAY COPYING IT IN A FILE MANAGER DOES."""
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
    """THE PASTEBOARD DIRECTLY, WHICH LEAVES BOTH THE NAMES A MAC APPLICATION LOOKS FOR."""
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