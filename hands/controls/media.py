"""WHATEVER IS PLAYING: PLAY, PAUSE, AND SKIPPING A TRACK."""

from hands.controls.commands import (
    REFUSED,
    UNSUPPORTED,
    on_mac,
    on_windows,
    osascript,
    powershell,
)

PLAY = "play"
PAUSE = "pause"
NEXT = "next"
PREVIOUS = "previous"

ACTIONS = (PLAY, PAUSE, NEXT, PREVIOUS)

WINDOWS_KEYS = {PLAY: 179, PAUSE: 179, NEXT: 176, PREVIOUS: 177}
WINDOWS_SEND = "(New-Object -ComObject WScript.Shell).SendKeys([char]{code})"

# MACOS HAS NO KEY WE CAN SEND, SO THE PLAYER ITSELF IS ASKED, IN THIS ORDER.
MAC_PLAYERS = ["Spotify", "Music"]
MAC_ACTIONS = {PLAY: "play", PAUSE: "pause", NEXT: "next track", PREVIOUS: "previous track"}

NOTHING = "Nothing is playing. Open a music app first."


def playing():
    """THE MEDIA APP THAT IS ACTUALLY OPEN, OR None."""
    for name in MAC_PLAYERS:
        open_now = osascript(
            f'tell application "System Events" to (name of processes) contains "{name}"'
        )

        if open_now == "true":
            return name

    return None


def control(action):
    wanted = (action or "").strip().lower()

    if wanted not in ACTIONS:
        return f"I can play, pause, or skip to the next or previous track, not {action}."

    if on_mac():
        player = playing()

        if player is None:
            return NOTHING

        done = osascript(f'tell application "{player}" to {MAC_ACTIONS[wanted]}')
        where = f" on {player}"
    elif on_windows():
        done = powershell(WINDOWS_SEND.format(code=WINDOWS_KEYS[wanted]))
        where = ""
    else:
        return UNSUPPORTED

    return f"{wanted.capitalize()}{where}." if done is not None else REFUSED
