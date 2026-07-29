"""THE CATALOGUE WITH THE LISTS ONLY A RUNNING MACHINE KNOWS FILLED IN.

WHICH MODELS ARE PULLED AND WHICH VOICES ARE INSTALLED ARE NOT THINGS A STATIC
CATALOGUE CAN HOLD, AND NEITHER IS HOW MANY SERVICES SOMEBODY HAS CONNECTED. SO
THE CONTROLS ARE FINISHED OFF HERE, ON THE WAY OUT TO THE WINDOW.
"""

import time

from memory import settings

# A LIST OF MODELS COSTS A ROUND TRIP TO THE BACKEND, SO IT IS NOT FETCHED AGAIN
# FOR EVERY NUDGE OF A SLIDER.
SOURCE_SECONDS = 30

CONNECTIONS = "mcps"

found = {}


def clear(name=None):
    """DROP A CACHED LIST, OR ALL OF THEM."""
    found.pop(name, None) if name else found.clear()


def drawn(reach=None):
    return [{**group, "settings": laid(group, reach)} for group in settings.groups()]


def laid(group, reach):
    """A GROUP'S CONTROLS. CONNECTIONS ARE NOT A LIST OF KNOBS AND ARE BUILT WHOLE.

    THE CATALOGUE'S OWN SETTINGS GO IN RATHER THAN ON TOP, BECAUSE WHERE THEY SIT
    AMONG THE SERVICES IS A THING ONLY THE CONNECTIONS THEMSELVES CAN DECIDE.
    """
    filled = [fill(entry) for entry in group["settings"]]

    if group["key"] != CONNECTIONS or reach is None:
        return filled

    try:
        return reach.drawn(filled)
    except Exception:  # A BROKEN CONNECTION MUST NOT LOSE EVERY OTHER CONTROL.
        return filled


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
