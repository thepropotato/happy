"""WHAT A SERVICE WANTS PASTED IN BEFORE IT CAN BE SIGNED INTO, AS BOXES.

THESE USED TO SIT IN THE PANEL IN THE OPEN, WHICH MEANT SIX EMPTY BOXES FOR
SECRETS BELONGING TO SERVICES NOBODY HAD SAID THEY WANTED. THEY LIVE INSIDE THE
SERVICE'S OWN ROW NOW AND ARE ONLY BUILT WHEN IT STILL WANTS SOMETHING.
"""

from mcps import directory
from memory.knobs import text

PASTE = "mcps.paste."

HELD = "Added — paste over it to change it"

# WHAT A SERVICE THAT WILL NOT REGISTER HAPPY ITSELF HAS TO BE GIVEN FIRST. THE
# SERVICE'S OWN NAME IS NOT IN THESE LABELS: THE BOX SITS INSIDE THAT SERVICE'S
# OWN ROW, AND SAYING "GMAIL CLIENT ID" UNDER THE WORD GMAIL WAS ONE READING OF
# THE SAME WORD TOO MANY.
ASKED = {
    directory.TOKEN: [("token", "Token", "Kept on this machine, never shown again.")],
    directory.CLIENT: [
        # SIGNING INTO YOUR OWN UNVERIFIED APP STILL GETS THE RED SCREEN, AND
        # SOMEBODY WHO WAS NOT WARNED READS IT AS HAPPY BEING THE UNSAFE PART.
        ("client", "Client ID", "It will warn that the app is unverified — it is yours. "
                                "Open Advanced and carry on."),
        ("secret", "Client secret", "From the same one."),
    ],
}


def wanted(known, compact):
    """THE BOXES THIS SERVICE STILL WANTS FILLED IN, IF IT WANTS ANY.

    A MEMBER OF A FAMILY NEVER HAS ITS OWN: THE ONE CLIENT THEY SHARE IS ASKED
    FOR ONCE, IN THE ROW ALL THREE OF THEM LIVE IN.
    """
    if compact or borrows(known["name"]):
        return []

    return boxes(known["name"], known["kind"])


def boxes(name, asking_for):
    """THE PASTE FIELDS FOR ONE SERVICE, SAYING WHICH OF THEM IT ALREADY HAS."""
    return [
        text(f"{PASTE}{name}.{field}", label, "", hint, HELD if given(name, field) else "")
        for field, label, hint in ASKED.get(asking_for, [])
    ]


def given(name, field):
    """TRUE WHEN SOMETHING IS ALREADY KEPT FOR THIS BOX. NEVER WHAT IT IS."""
    from mcps import signing, tokens

    if field == "token":
        return bool((tokens.kept(name).get("tokens") or {}).get("access_token"))

    held = signing.client(name)

    return bool(held.get("client_secret" if field == "secret" else "client_id"))


def borrows(name):
    """TRUE WHEN A SERVICE THIS ONE SHARES A SIGN IN WITH ALREADY HAS THE CLIENT."""
    from mcps import signing, tokens

    own = tokens.kept(name).get("client") or {}

    return not own.get("client_id") and bool(signing.client(name).get("client_id"))


def poised(name, kind):
    """TRUE WHEN PRESSING CONNECT WOULD ACTUALLY GET SOMEWHERE."""
    from mcps import signing

    try:
        return signing.ready(name, kind)
    except Exception:
        return False
