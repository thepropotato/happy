"""THE CONNECTIONS AS CONTROLS, SO THE WINDOW CAN DRAW THEM WITHOUT KNOWING ANY.

THE CATALOGUE HOLDS A FIXED LIST OF KNOBS AND THIS IS NOT ONE: HOW MANY THERE ARE
DEPENDS ON WHAT SOMEBODY HAS CONNECTED. SO THE ROWS ARE MADE HERE, IN THE SAME
SHAPE memory/knobs.py PRODUCES, AND THE WINDOW CANNOT TELL THE DIFFERENCE.
"""

from mcps import directory, store, tokens
from memory.knobs import action, text, toggle

ON = "mcps.on."

PASTE = "mcps.paste."

NEW = "mcps.new"

# WHAT A SERVICE THAT WILL NOT REGISTER HAPPY ITSELF HAS TO BE GIVEN FIRST.
ASKED = {
    directory.TOKEN: [("token", "Token", "Pasted from the service. Kept, never shown again.")],
    directory.CLIENT: [
        # SIGNING INTO YOUR OWN UNVERIFIED APP STILL GETS THE RED SCREEN, AND
        # SOMEBODY WHO WAS NOT WARNED READS IT AS HAPPY BEING THE UNSAFE PART.
        ("client", "Client ID", "From the OAuth client you made. It will warn that the app is "
                                "unverified — it is yours. Open Advanced and carry on."),
        ("secret", "Client secret", "From the same one."),
    ],
}

ADDED = "Anything else"

ADDING = "A web address, or a command to run. Enter adds it."

SIGN_OUT = "Sign out"

CONNECT = "Connect"

SWITCH_ON = "Switch on"


def rows():
    """ONE OR TWO CONTROLS PER SERVICE, PLUS THE BOX FOR ANYTHING NOT LISTED."""
    kept = {row["name"]: row for row in store.every()}
    drawn = []

    for known in directory.known():
        drawn.extend(service(known, kept.pop(known["name"], None)))

    for name, row in kept.items():  # WHATEVER SOMEBODY ADDED THEMSELVES.
        drawn.extend(service({"name": name, "label": row["label"], "hint": ""}, row))

    drawn.append(text(NEW, ADDED, "", ADDING, "https://example.com/mcp"))

    return drawn


def service(known, row):
    """WHAT ONE SERVICE LOOKS LIKE RIGHT NOW: A BUTTON, OR A SWITCH AND A WAY OUT."""
    name, label = known["name"], known["label"]

    if row is not None and row["tools"]:
        return [
            toggle(ON + name, label, row["enabled"], trouble(row) or counted(row)),
            action(name, f"{label} sign in", "disconnect", SIGN_OUT, None),
        ]

    # WHAT THIS ONE WANTS PASTED IN BEFORE THE BUTTON CAN DO ANYTHING. A SERVICE
    # THAT REGISTERS HAPPY ITSELF ASKS FOR NOTHING AND IS THE ONE BUTTON CASE, AND
    # SO IS ONE WHOSE SISTER SERVICE ALREADY HAS THE CLIENT THEY BOTH USE.
    if borrows(name):
        return [action(name, label, "connect", CONNECT, directory.ALSO_GOOGLE)]

    boxes = [
        text(f"{PASTE}{name}.{field}", f"{label} {said}", "", hint)
        for field, said, hint in ASKED.get(known.get("kind"), [])
    ]

    return boxes + [action(name, label, "connect", wording(known), trouble(row) or known["hint"])]


def borrows(name):
    """TRUE WHEN A SERVICE THIS ONE SHARES A SIGN IN WITH ALREADY HAS THE CLIENT."""
    from mcps import signing

    mine = tokens.kept(name).get("client") or {}

    return not mine.get("client_id") and bool(signing.client(name).get("client_id"))


def wording(known):
    """A SERVICE THAT ONLY NEEDS SWITCHING ON SHOULD NOT SAY Connect."""
    return SWITCH_ON if known.get("kind") == directory.LOCAL else CONNECT


def counted(row):
    return f"{len(row['tools'])} tools."


def trouble(row):
    return row["state"] if row else None


def values():
    """WHAT EACH GENERATED SWITCH IS SET TO. BUTTONS AND BOXES HOLD NOTHING."""
    return {ON + row["name"]: row["enabled"] for row in store.every()}
