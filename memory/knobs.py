"""WHAT A SETTING IS: A KIND, A DEFAULT, AND ENOUGH FOR A CONTROL TO DRAW ITSELF.

THE CATALOGUE IS BUILT OUT OF THESE. NOTHING HERE KNOWS WHAT ANY PARTICULAR
SETTING MEANS, ONLY HOW ONE IS SHAPED AND HOW A TYPED-IN VALUE IS MADE SAFE.
"""

ACTION = "action"
CHOICE = "choice"
NUMBER = "number"
TEXT = "text"
TOGGLE = "toggle"

# THREE SHAPES THAT ARE NOT SETTINGS: A LIST OF SERVICES IS NOT A LIST OF KNOBS.
HEADING = "heading"
SERVICE = "service"
FOLDED = "folded"


def choice(key, label, options, default, hint=None, source=None, rare=False):
    """ONE OF A FEW. source NAMES A LIST THAT ONLY THE RUNNING MACHINE KNOWS."""
    return knob(
        key,
        label,
        CHOICE,
        default,
        hint,
        rare,
        options=[option(each) for each in options],
        source=source,
    )


def number(key, label, low, high, step, default, hint=None, unit=None, whole=False, rare=False):
    return knob(
        key, label, NUMBER, default, hint, rare, low=low, high=high, step=step, unit=unit,
        whole=whole
    )


def text(key, label, default="", hint=None, placeholder=None, rare=False):
    return knob(key, label, TEXT, default, hint, rare, placeholder=placeholder)


def toggle(key, label, default=False, hint=None, rare=False):
    return knob(key, label, TOGGLE, default, hint, rare)


def action(key, label, verb, wording, hint=None):
    """A BUTTON, NOT A SETTING. NOTHING IS KEPT: PRESSING IT ASKS FOR SOMETHING.

    THE CONTROL DRAWS ITSELF THE SAME WAY EVERY OTHER ONE DOES, SO A THING THAT
    HAS TO BE DONE RATHER THAN CHOSEN COSTS THE WINDOW NO NEW IDEAS.
    """
    return knob(key, label, ACTION, None, hint, verb=verb, wording=wording)


def knob(key, label, kind, default, hint, rare=False, **extra):
    """rare KEEPS A SETTING OUT OF THE WAY WITHOUT KEEPING IT SECRET: ITS SECTION
    HOLDS IT BEHIND ONE MORE TAP, BECAUSE A SHEET WHERE EVERY KNOB IS AS LOUD AS
    EVERY OTHER ONE IS A SHEET NOBODY READS."""
    return {
        "key": key,
        "label": label,
        "kind": kind,
        "default": default,
        "hint": hint,
        "rare": rare,
        **extra,
    }


def option(each):
    """A CHOICE IS EITHER A BARE VALUE OR A VALUE WITH SOMETHING NICER TO READ."""
    if isinstance(each, (tuple, list)):
        return {"value": each[0], "label": each[1]}

    return {"value": each, "label": str(each)}


def heading(label, count=None):
    """WORDS OVER A RUN OF ROWS. NOTHING TO SET AND NOTHING TO PRESS."""
    return {"key": f"heading.{label}", "label": label, "kind": HEADING, "count": count}


def service(name, label, mark, under, **extra):
    """A WHOLE CONNECTION AS ONE ROW, AND WHAT OPENS UNDER IT WHEN IT IS TAPPED.

    key IS THE SWITCH'S SETTING, WHICH ONLY EXISTS ONCE THERE IS SOMETHING TO
    SWITCH. fields, action AND leaving ARE ORDINARY KNOBS, SO WHAT IS INSIDE THE
    ROW IS DRAWN BY THE SAME CODE THAT DRAWS EVERYTHING ELSE.

    NONE OF IT REACHES THE LIST. THE ROW ITSELF IS A NAME, A LINE AND A CHEVRON ON
    EVERY CONNECTION WITHOUT EXCEPTION, AND ALL OF THIS OPENS UNDERNEATH IT.
    """
    return {
        "key": None,
        "kind": SERVICE,
        "name": name,
        "label": label,
        "mark": mark,
        "under": under,
        "tone": "",  # live, warn, OR NOTHING AT ALL.
        "careful": False,
        "connected": False,
        "ready": True,  # FALSE DIMS THE BUTTON: PRESSING IT NOW WOULD GET NOWHERE.
        "signed": 0,
        "tools": 0,
        "doing": [],  # THE TOOL NAMES IT ACTUALLY HANDS OVER.
        "note": None,
        "fields": [],
        "parts": [],
        "action": None,
        "leaving": [],
        **extra,
    }


def folded(key, label, mark, settings):
    """A ROW THAT OPENS INTO ORDINARY CONTROLS. WHAT IS RARELY TOUCHED LIVES IN ONE."""
    return {"key": key, "label": label, "kind": FOLDED, "mark": mark, "settings": settings}


def group(key, label, hint, settings, sums=None):
    """sums NAMES THE SETTINGS WHOSE VALUES SAY WHAT THIS SECTION IS SET TO, FOR
    SOMEBODY WHO CAME TO CHECK RATHER THAN TO CHANGE. WITH NONE, THE HINT DOES."""
    return {"key": key, "label": label, "hint": hint, "sums": sums or [], "settings": settings}


def settle(entry, value):
    """A VALUE THAT CAME FROM OUTSIDE, MADE INTO ONE THIS SETTING CAN HOLD."""
    kind = entry["kind"]

    if kind == ACTION:
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
