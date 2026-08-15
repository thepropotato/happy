"""THE CATALOGUE WITH THE LISTS ONLY A RUNNING MACHINE KNOWS FILLED IN."""

import time

from memory import settings

# A LIST OF MODELS COSTS A ROUND TRIP TO THE BACKEND, SO IT IS CACHED.
SOURCE_SECONDS = 30

CONNECTIONS = "mcps"

found = {}


def clear(name=None):
    """DROP A CACHED LIST, OR ALL OF THEM."""
    found.pop(name, None) if name else found.clear()


def drawn(reach=None):
    return [{**group, "settings": controls(group, reach)} for group in settings.groups()]


def controls(group, reach):
    """A GROUP'S CONTROLS."""
    filled = [fill(entry) for entry in group["settings"]]

    if group["key"] != CONNECTIONS or reach is None:
        return filled

    try:
        return reach.drawn(filled)
    except Exception:
        return filled


def fill(entry):
    source = entry.get("source")

    if not source:
        return entry

    offered = sourced(source)
    here = settings.get(entry["key"])

    # WHAT IS SET STAYS IN THE LIST, SO THE CONTROL NEVER BLANKS A WORKING SETTING.
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

        if name == "microphones":
            from ears import microphone

            return microphone.offered()
    except Exception:
        pass

    return []
