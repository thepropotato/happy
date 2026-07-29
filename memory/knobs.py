"""WHAT A SETTING IS: A KIND, A DEFAULT, AND ENOUGH FOR A CONTROL TO DRAW ITSELF.

THE CATALOGUE IS BUILT OUT OF THESE. NOTHING HERE KNOWS WHAT ANY PARTICULAR
SETTING MEANS, ONLY HOW ONE IS SHAPED AND HOW A TYPED-IN VALUE IS MADE SAFE.
"""

ACTION = "action"
CHOICE = "choice"
NUMBER = "number"
TEXT = "text"
TOGGLE = "toggle"


def choice(key, label, options, default, hint=None, source=None):
    """ONE OF A FEW. source NAMES A LIST THAT ONLY THE RUNNING MACHINE KNOWS."""
    return knob(
        key,
        label,
        CHOICE,
        default,
        hint,
        options=[option(each) for each in options],
        source=source,
    )


def number(key, label, low, high, step, default, hint=None, unit=None, whole=False):
    return knob(
        key, label, NUMBER, default, hint, low=low, high=high, step=step, unit=unit, whole=whole
    )


def text(key, label, default="", hint=None, placeholder=None):
    return knob(key, label, TEXT, default, hint, placeholder=placeholder)


def toggle(key, label, default=False, hint=None):
    return knob(key, label, TOGGLE, default, hint)


def action(key, label, verb, wording, hint=None):
    """A BUTTON, NOT A SETTING. NOTHING IS KEPT: PRESSING IT ASKS FOR SOMETHING.

    THE CONTROL DRAWS ITSELF THE SAME WAY EVERY OTHER ONE DOES, SO A THING THAT
    HAS TO BE DONE RATHER THAN CHOSEN COSTS THE WINDOW NO NEW IDEAS.
    """
    return knob(key, label, ACTION, None, hint, verb=verb, wording=wording)


def knob(key, label, kind, default, hint, **extra):
    return {"key": key, "label": label, "kind": kind, "default": default, "hint": hint, **extra}


def option(each):
    """A CHOICE IS EITHER A BARE VALUE OR A VALUE WITH SOMETHING NICER TO READ."""
    if isinstance(each, (tuple, list)):
        return {"value": each[0], "label": each[1]}

    return {"value": each, "label": str(each)}


def group(key, label, hint, settings):
    return {"key": key, "label": label, "hint": hint, "settings": settings}


def settle(entry, value):
    """A VALUE THAT CAME FROM OUTSIDE, MADE INTO ONE THIS SETTING CAN HOLD."""
    kind = entry["kind"]

    if kind == ACTION:  # A BUTTON HOLDS NOTHING, SO THERE IS NOTHING TO SETTLE.
        return None

    if kind == TOGGLE:
        return truth(value)

    if kind == NUMBER:
        return bounded(entry, value)

    if kind == CHOICE and entry.get("options") and not entry.get("source"):
        allowed = [each["value"] for each in entry["options"]]

        return value if value in allowed else entry["default"]

    return "" if value is None else str(value)


def truth(value):
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")

    return bool(value)


def bounded(entry, value):
    try:
        wanted = float(value)
    except (TypeError, ValueError):
        return entry["default"]

    wanted = min(max(wanted, entry["low"]), entry["high"])

    return int(round(wanted)) if entry.get("whole") else round(wanted, 4)
