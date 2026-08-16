"""WHAT THE WINDOW ASKS FOR: ONE JSON OBJECT PER LINE, READ OFF STDIN."""

import json
import sys
import threading

import memory
from face import sources, telling
from memory import settings

RECENT_MESSAGES = 60

# A KNOB THAT DECIDES WHAT THE NEXT ONE OFFERS.
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

    reader = threading.Thread(target=listen, daemon=True)
    reader.start()

    return reader


def listen():
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
            telling.trouble(error)

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
        call("ready")  # A KNOB CAN CHANGE WHAT THE PANEL SAYS ABOUT ITSELF.
    elif asked == "reset":
        settings.clear(order.get("key"))
        describe()
        call("ready")
    elif asked in REACHING:
        # A SIGN IN IS MINUTES. HOLDING THIS THREAD WOULD MUTE THE WINDOW.
        threading.Thread(target=reaching, args=(asked, order.get("name")), daemon=True).start()
    elif asked == "history":
        recall(order.get("limit", RECENT_MESSAGES))
    elif asked == "logs":
        logs()
    elif asked == "allow":
        granting(order.get("name"))
    elif asked == "say":
        call("say", order.get("text", ""))
    elif asked == "preview":
        # THE NAME IS THE OPTION THE BUTTON SITS BESIDE, WHICH IS NOT THE ONE THAT IS SET.
        call("preview", order.get("name"))
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
        # WHAT CONNECTING SAYS NEVER REACHES THE CONVERSATION: THAT STREAM IS WHAT
        # HAPPY AND A PERSON SAID, AND THE SERVICE'S OWN ROW IS ALREADY SAYING THIS.
        if asked == "connect":
            reach.connect(name)
        else:
            reach.disconnect(name)
    except Exception as error:
        telling.trouble(error)

    describe()


def granting(name):
    """ASK THE SYSTEM FOR ONE PERMISSION, THEN REDRAW: THE ANSWER MAY ALREADY BE IN."""
    from face import allowing

    try:
        allowing.grant(name)
    except Exception as error:
        telling.trouble(error)

    describe()
    call("ready")  # THE BANNER NAMES WHAT IS STILL MISSING.


def connections():
    """THE CONNECTIONS, IF THEY LOAD. A BROKEN ONE MUST NOT STOP THE PANEL."""
    try:
        import mcps

        return mcps
    except Exception:
        return None


def describe():
    reach = connections()

    telling.send("settings", groups=sources.drawn(reach), values=dict(settings.every()))


def recall(limit):
    telling.send("history", messages=memory.history(limit=max(1, int(limit))))


def logs():
    """WRITE THE PAGE OUT AND HAND THE WINDOW SOMETHING TO OPEN IT WITH."""
    try:
        telling.send("open", url=memory.exported().as_uri())
    except Exception as error:
        telling.trouble(error)
