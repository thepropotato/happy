"""WHAT THE WINDOW ASKS FOR: ONE JSON OBJECT PER LINE, READ OFF STDIN.

READING HAPPENS ON ITS OWN THREAD, BECAUSE THE LOOP IN main.py SPENDS MOST OF
ITS LIFE WAITING ON A KEY AND WOULD OTHERWISE ANSWER NOTHING UNTIL SOMEONE SPOKE.
"""

import json
import sys
import threading

import memory
from face import panel, sources
from memory import settings

RECENT_MESSAGES = 60

# A KNOB THAT DECIDES WHAT THE NEXT ONE OFFERS. MOVING IT DROPS THAT CACHED LIST.
# ONLY THESE, BECAUSE ASKING A BACKEND WHAT IT HAS IS A ROUND TRIP PER NUDGE.
GOVERNS = {"brain.provider": "models", "brain.url": "models"}

PASTE = "mcps.paste."

REACHING = ("connect", "disconnect")

doing = {}


def serve(**handlers):
    """START LISTENING. handlers NAME THE THINGS ONLY main.py CAN DO."""
    doing.update(handlers)

    reach = connections()

    # A QR SCANNED IN A BROWSER TAB IS THE ONE CHANGE THE WINDOW CANNOT ASK ABOUT,
    # BECAUSE IT NEVER TOUCHED THIS PANEL AT ALL. SO THE PANEL IS TOLD INSTEAD.
    if reach is not None:
        reach.whenever(describe)

    reader = threading.Thread(target=read, daemon=True)
    reader.start()

    return reader


def read():
    for line in sys.stdin:
        line = line.strip()

        if not line:
            continue

        try:
            order = json.loads(line)
        except ValueError:
            continue

        try:
            carry(order)
        except Exception as error:
            panel.trouble(error)

    call("quit")


def carry(order):
    asked = order.get("do")

    if asked in ("hello", "refresh"):
        sources.clear()
        describe()
        recall(order.get("limit", RECENT_MESSAGES))
    elif asked == "settings":
        describe()
    elif asked == "set":
        changed(order.get("key"), order.get("value"))
        governed = GOVERNS.get(order.get("key"))

        if governed:  # clear() WITH NOTHING DROPS EVERY LIST, WHICH IS NOT THE ASK.
            sources.clear(governed)

        describe()
    elif asked == "reset":
        settings.clear(order.get("key"))
        describe()
    elif asked in REACHING:
        # A SIGN IN IS MINUTES. HOLDING THIS THREAD WOULD MUTE THE WINDOW.
        threading.Thread(target=reaching, args=(asked, order.get("name")), daemon=True).start()
    elif asked == "history":
        recall(order.get("limit", RECENT_MESSAGES))
    elif asked == "answer":
        panel.answered(order.get("id"), order.get("yes"))
    elif asked == "say":
        call("say", order.get("text", ""))
    else:
        call(asked)


def call(what, *args):
    handler = doing.get(what)

    if handler:
        handler(*args)


def changed(key, value):
    """A KNOB MOVED. MOST ARE ORDINARY SETTINGS, A FEW ARE CONNECTIONS."""
    reach = connections()
    key = str(key or "")

    if reach is None:
        settings.put(key, value)
    elif key.startswith(PASTE):
        reach.paste(key[len(PASTE) :], value)
    else:
        settings.put(key, value)


def reaching(asked, name):
    """CONNECTING, ON ITS OWN THREAD, TELLING THE WINDOW HOW IT WENT."""
    reach = connections()

    if reach is None or not name:
        return

    try:
        # WHAT CONNECTING HAD TO SAY IS NOT SAID IN THE CONVERSATION. THAT STREAM IS
        # WHAT HAPPY AND A PERSON SAID TO EACH OTHER, AND "SCAN THE QR IN YOUR
        # BROWSER" IS NEITHER. THE SERVICE'S OWN ROW IS ALREADY SAYING IT, WHICH IS
        # WHERE SOMEBODY WHO JUST PRESSED THE BUTTON IS LOOKING.
        if asked == "connect":
            reach.connect(name)
        else:
            reach.disconnect(name)
    except Exception as error:
        panel.trouble(error)

    describe()


def connections():
    """THE CONNECTIONS, IF THEY LOAD. A BROKEN ONE MUST NOT STOP THE PANEL."""
    try:
        import mcps

        return mcps
    except Exception:
        return None


def describe():
    reach = connections()

    panel.send("settings", groups=sources.drawn(reach), values=dict(settings.every()))


def recall(limit):
    panel.send("history", messages=memory.history(limit=max(1, int(limit))))
