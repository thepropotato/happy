"""WHAT IS ON THE CLIPBOARD, AND PUTTING SOMETHING THERE."""

from hands.controls.commands import (
    REFUSED,
    UNSUPPORTED,
    on_mac,
    on_windows,
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
