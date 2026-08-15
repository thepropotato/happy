"""THE SCREEN AS STRUCTURE RATHER THAN AS PIXELS."""

from eyes import attention, systems

# BELOW THIS MANY NAMED CONTROLS, THE WORDS ON SCREEN ARE WORTH AN OCR PASS.
THIN = 4

# A CONTAINER WITH NO NAME IS SCAFFOLDING, KEPT ONLY WHEN IT SAYS SOMETHING: A
# NAMED GROUP IS OFTEN THE ONLY THING HOLDING A DIALOG'S TITLE.
SCAFFOLDING = (
    "group",
    "area",
    "scroll area",
    "layout area",
    "layout item",
    "split group",
    "row",
    "cell",
    "column",
    "splitter",
    "scroll bar",
    "value indicator",
    "unknown",
)


def readable():
    """WHY THE STRUCTURE CANNOT BE READ, OR None WHEN IT CAN."""
    return attention.allowed()


def tree():
    """EVERY CONTROL IN THE APPLICATION IN FRONT, IN READING ORDER."""
    if readable() is not None:
        return []

    name, handle = attention.front()

    if handle is None:
        return []

    try:
        if attention.on_mac():
            found = systems.mac_elements(handle)
        elif attention.on_windows():
            found = systems.windows_elements(handle)
        else:
            return []
    except Exception:
        return []

    return order(prune(found))


def prune(found):
    """THE SAME ELEMENTS WITHOUT THE SCAFFOLDING AND WITHOUT THE REPEATS."""
    kept, seen = [], set()

    for element in found:
        if element.kind in SCAFFOLDING and not element.label:
            continue

        mark = (element.said.lower(), element.left, element.top, element.width, element.height)

        if mark in seen:
            continue

        seen.add(mark)
        kept.append(element)

    return kept


def order(found):
    """READING ORDER, SO A LISTING OF THEM READS LIKE THE SCREEN LOOKS."""
    return sorted(found, key=lambda element: (element.top, element.left))


def inside(found):
    """THE CONTROLS THAT ARE ACTUALLY IN THE WINDOW."""
    return [
        element
        for element in found
        if element.said and element.kind not in ("menu", "window") and element.kind not in SCAFFOLDING
    ]


def thin(found):
    """TRUE WHEN THE APPLICATION HAS NOT REALLY SAID WHAT IS IN ITS WINDOW."""
    return len(inside(found)) < THIN
