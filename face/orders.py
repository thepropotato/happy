"""WHAT THE WINDOW ASKS FOR: ONE JSON OBJECT PER LINE, READ OFF STDIN.

READING HAPPENS ON ITS OWN THREAD, BECAUSE THE LOOP IN main.py SPENDS MOST OF
ITS LIFE WAITING ON A KEY AND WOULD OTHERWISE ANSWER NOTHING UNTIL SOMEONE SPOKE.
"""

import json
import sys
import threading
import time

import memory
from face import panel
from memory import settings

# A LIST OF MODELS COSTS A ROUND TRIP TO THE BACKEND, SO IT IS NOT FETCHED AGAIN
# FOR EVERY NUDGE OF A SLIDER.
SOURCE_SECONDS = 30

RECENT_MESSAGES = 60

# A KNOB THAT DECIDES WHAT THE NEXT ONE OFFERS. MOVING IT DROPS THAT ONE CACHED
# LIST, RATHER THAN LEAVING THE CONTROL SHOWING THE OLD BACKEND'S MODELS FOR HALF
# A MINUTE. ONLY THESE, BECAUSE A SLIDER FIRES ONE SET PER NUDGE AND ASKING A
# BACKEND WHAT IT HAS IS A ROUND TRIP.
GOVERNS = {"brain.provider": "models", "brain.url": "models"}

doing = {}
found = {}


def serve(**handlers):
    """START LISTENING. handlers NAME THE THINGS ONLY main.py CAN DO."""
    doing.update(handlers)

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
        except Exception as error:  # A BAD ORDER IS NOT A REASON TO STOP LISTENING.
            panel.trouble(error)

    call("quit")  # THE WINDOW CLOSED ITS END. THERE IS NOBODY LEFT TO TALK TO.


def carry(order):
    asked = order.get("do")

    if asked in ("hello", "refresh"):
        found.clear()
        describe()
        recall(order.get("limit", RECENT_MESSAGES))
    elif asked == "settings":
        describe()
    elif asked == "set":
        settings.put(order.get("key"), order.get("value"))
        governed = GOVERNS.get(order.get("key"))

        if governed:  # DROPPING EVERY LIST IS NOT THE ASK, ONLY THE ONE IT DECIDES.
            found.pop(governed, None)

        describe()
    elif asked == "reset":
        settings.clear(order.get("key"))
        describe()
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


def describe():
    panel.send("settings", groups=drawn(), values=settings.every())


def recall(limit):
    panel.send("history", messages=memory.history(limit=max(1, int(limit))))


def drawn():
    """THE CATALOGUE WITH THE LISTS ONLY A RUNNING MACHINE KNOWS FILLED IN."""
    return [
        {**group, "settings": [fill(entry) for entry in group["settings"]]}
        for group in settings.groups()
    ]


def fill(entry):
    source = entry.get("source")

    if not source:
        return entry

    offered = sourced(source)
    here = settings.get(entry["key"])

    # WHAT IS SET STAYS IN THE LIST EVEN WHEN THE BACKEND IS DOWN AND OFFERS
    # NOTHING, SO THE CONTROL NEVER SHOWS A BLANK FOR A WORKING SETTING.
    if here and here not in offered:
        offered = [here] + offered

    return {**entry, "options": [{"value": each, "label": each} for each in offered], "open": True}


def sourced(name):
    kept = found.get(name)

    if kept and time.monotonic() - kept[0] < SOURCE_SECONDS:
        return kept[1]

    offered = ask(name)
    found[name] = (time.monotonic(), offered)

    return offered


def ask(name):
    try:
        if name == "models":
            from brain import model

            return model.offered()

        if name == "voices":
            import voice

            return voice.installed()
    except Exception:  # NOTHING TO OFFER IS A SHORTER LIST, NOT A FAILURE.
        pass

    return []
