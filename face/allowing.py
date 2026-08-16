"""THE PERMISSIONS AS ROWS, AND THE BUTTON THAT GOES AND GETS ONE."""

import subprocess
import sys

from memory.kinds import action, state

MACOS = "darwin"
WINDOWS = "win32"

KEY = "allow."
VERB = "allow"

# WHAT THE BUTTON SAYS, WHICH IS ALSO WHAT PRESSING IT WILL DO.
ASK = "Allow"
OPEN = "Open Settings"
FINE = "Allowed"

ASKED = "Happy is waiting on this one."
REFUSED = "Turned off. The button opens the pane it lives in."
UNKNOWN = "Windows will not say whether this is on. The button opens the pane it lives in."

# ONE URL PER PANE, AND THE SYSTEM OPENS SETTINGS ON IT.
SETTINGS = "x-apple.systempreferences:com.apple.preference.security?{pane}"

# WINDOWS KEEPS THE MICROPHONE SWITCH SOMEWHERE ENTIRELY ITS OWN.
WINDOWS_PANES = {"microphone": "ms-settings:privacy-microphone"}


def every():
    """EVERY PERMISSION HAPPY WANTS, FROM WHICHEVER SENSE NEEDS IT."""
    from ears import allowing as hearing
    from eyes import allowing as looking

    return (*hearing.EVERY, *looking.EVERY)


def gathered():
    """EACH ONE THIS SYSTEM ACTUALLY WITHHOLDS, WITH ITS ANSWER READ FRESH.

    None is not the same as no: on a Mac it is a question that has not been put yet, and
    on Windows it is a switch that exists but that no program is allowed to read.
    """
    found = []

    for each in every():
        try:
            if not each["gated"]():
                continue

            answer = each["allowed"]()
        except Exception:
            continue

        found.append((each, answer))

    return found


def drawn():
    """THE ROWS THE PANEL SHOWS. NOTHING HERE IS STORED, SO NONE OF THEM IS A SETTING."""
    rows = []

    for each, answer in gathered():
        key = f"{KEY}{each['name']}"

        # ONE ALREADY GRANTED HAS NOTHING TO PRESS, AND A BUTTON SAYING "ALLOWED" ONLY
        # INVITES A PRESS THAT GOES NOWHERE.
        if answer:
            rows.append(state(key, each["label"], FINE, each["hint"]))
        else:
            rows.append(
                action(key, each["label"], VERB, wording(answer), hint(each, answer),
                       instant=True)
            )

    return rows


def prompting():
    """TRUE WHERE THE SYSTEM WILL PUT UP A DIALOG IF WE ASK IT TO."""
    return sys.platform == MACOS


def wording(answer):
    # AN UNKNOWN ANSWER ON WINDOWS IS NOT A QUESTION WAITING TO BE PUT, IT IS A SWITCH
    # NOBODY CAN READ, SO THE ONLY HONEST BUTTON IS THE ONE THAT GOES AND SHOWS IT.
    if answer is None and not prompting():
        return OPEN

    return OPEN if answer is False else ASK


def hint(each, answer):
    if answer:
        return each["hint"]

    if answer is None and not prompting():
        return f"{each['hint']} {UNKNOWN}"

    return f"{each['hint']} {REFUSED if answer is False else ASKED}"


def short(answer):
    """TRUE WHERE THIS ONE IS REALLY MISSING, RATHER THAN MERELY UNREADABLE."""
    return answer is False or (answer is None and prompting())


def missing():
    """THE LABELS OF THE ONES STILL NOT GRANTED, FOR A BANNER OR A STARTUP LINE."""
    return [each["label"] for each, answer in gathered() if short(answer)]


# THE SYSTEM PUTS THESE THREE UP ONCE AND NEVER AGAIN, SO ASKING AT EVERY START IS FREE.
ONCE = ("microphone", "screen", "keys")


def asked():
    """ASK FOR ANYTHING NEVER ASKED ABOUT, AND CARRY ON WITHOUT WAITING FOR AN ANSWER.

    Accessibility is left out on purpose: its dialog is the only one the system will put
    up again on every single launch, and a prompt that appears every time is a prompt
    nobody reads. It is asked for from its row in Settings instead.
    """
    for each in every():
        if each["name"] not in ONCE:
            continue

        try:
            if each["allowed"]() is not True:
                each["ask"]()
        except Exception:
            pass


def grant(key):
    """THE BUTTON. ASK THE SYSTEM WHERE IT WILL STILL ASK, OR GO TO THE SWITCH."""
    name = str(key or "").removeprefix(KEY)

    for each in every():
        if each["name"] != name:
            continue

        try:
            answer = each["allowed"]()
        except Exception:
            answer = None

        # A REFUSAL IS REMEMBERED BY THE SYSTEM AND NO DIALOG WILL COME BACK, SO THE ONLY
        # THING LEFT TO DO IS PUT THE RIGHT PANE IN FRONT OF SOMEBODY.
        if answer is False or not each["ask"]():
            return show(each)

        # ACCESSIBILITY AND THE KEY NEVER FLIP FOR A PROCESS THAT IS ALREADY RUNNING, SO
        # THEIR DIALOG IS ONLY EVER HALF THE ANSWER: THE PANE IS OPENED BEHIND IT EITHER WAY.
        if each["name"] in ("controls", "keys"):
            show(each)

        return True

    return False


def show(each):
    """PUT THE PANE HOLDING THIS SWITCH IN FRONT."""
    if sys.platform == MACOS:
        return opened(["open", SETTINGS.format(pane=each["pane"])])

    if sys.platform == WINDOWS:
        where = WINDOWS_PANES.get(each["name"])

        return opened(["cmd", "/c", "start", "", where]) if where else False

    return False


def opened(command):
    try:
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return True
    except OSError:
        return False
