"""THE ONE TOOL: WHAT IS CONNECTED, WHAT IS NOT, AND WHAT SOMEBODY DOES ABOUT EITHER."""

from langchain_core.tools import tool

from mcps import registry, store, tokens, wording

# NOTHING HERE CHANGES ANYTHING: EVERY SENTENCE IT WRITES ENDS AT A ROW SOMEBODY PRESSES.
PLACE = "It is all done in Happy's settings, under Connections, each service in its own row."

OUT = "Sign out in its row."

PRESS = "Nothing to sign into: press Connect in its row."

SCAN = "Press Connect in its row and scan the QR that appears with your phone."

HELD = "Its token is saved already: press Connect in its row."

TOKEN = "Make a token at {where}, paste it into the Token box in its row, then press Connect."

READY = "Press Sign into {label} in its row and say yes on the page that opens."

APP = (
    "Make an OAuth client at {where}. "
    + registry.SENDS_BACK
    + " Paste the client ID and the client secret into its row, then press Sign into {label}."
)

HALF = "Paste its {wanted} into its row, then press Sign into {label}."

# THE TWO HALVES OF AN OAUTH CLIENT, IN THE ORDER SOMEBODY IS ASKED FOR THEM.
HALVES = [("client_id", "client ID"), ("client_secret", "client secret")]


@tool
def connections(service: str = "") -> str:
    """Say which outside services are connected and which are not, how many tools each
    connected one brings, and exactly what the person does to connect or sign out of
    each one. Name one service to hear about only that one, and call it with nothing to
    hear about all of them.

    Use this when you are asked what you can reach, what is connected, how many are,
    or how one of them is connected or disconnected. It says nothing about this
    computer.

    Connecting and signing out are the person's to do, in Happy's settings, and neither
    is yours: say back what this tells you and leave the pressing to them."""
    if not (service or "").strip():
        return report()

    known = registry.matched(service)

    if known is None:
        return nope(f"There is nothing called {service}. There is {listed()}.")

    return report(known["name"])


def report(name=""):
    """EVERY SERVICE AND WHERE IT STANDS, OR ONLY THE ONE ASKED ABOUT."""
    asked = [registry.one(name)] if name else registry.known()
    kept = {row["name"]: row for row in store.every()}
    lines = [standing(each, kept.get(each["name"])) for each in asked]

    if name:
        return f"{lines[0]} {PLACE}"

    live = sum(1 for each in asked if connected(each, kept.get(each["name"])))

    return "\n".join([f"{live} of {len(asked)} connected. {PLACE}"] + lines)


def standing(known, row):
    """ONE SERVICE ON ONE LINE: WHERE IT STANDS, AND THE ONE THING LEFT TO DO ABOUT IT."""
    if connected(known, row):
        said = f"{known['label']}: connected, {wording.numbered(len(row['tools']))}. {OUT}"
    else:
        said = f"{known['label']}: not connected. {how(known)}"

    return f"{said} Last trouble: {wording.ended(row['state'])}" if trouble(row) else said


def connected(known, row):
    """REMEMBERING TOOLS IS CONNECTED, EXCEPT WHERE A QR STILL HAS TO BE SCANNED."""
    if not row or not row["tools"]:
        return False

    if known.get("scan"):
        from mcps import bridging

        return bridging.linked()

    return True


def how(known):
    """WHAT SOMEBODY DOES TO CONNECT THIS ONE, IN A SENTENCE THAT CAN BE SAID OUT LOUD."""
    name, kind, label = known["name"], known["kind"], known["label"]

    if kind == registry.TOKEN:
        return HELD if tokens.signed(name) else TOKEN.format(where=plain(known))

    if kind == registry.OAUTH:
        wanted = lacking(name)

        if not wanted:
            return READY.format(label=label)

        if len(wanted) == 1:
            return HALF.format(wanted=wanted[0], label=label)

        return APP.format(where=plain(known), label=label)

    return SCAN if known.get("scan") else PRESS


def lacking(name):
    """WHICH HALVES OF AN OAUTH CLIENT ARE NOT SAVED YET."""
    held = tokens.client(name)

    return [said for field, said in HALVES if not held.get(field)]


def plain(known):
    """A SERVICE'S PAGE WITHOUT THE https:// IN FRONT OF IT, WHICH NOBODY SAYS ALOUD."""
    return (known.get("where") or "").split("://")[-1].rstrip("/")


def listed():
    labels = [each["label"] for each in registry.known()]

    return f"{', '.join(labels[:-1])} and {labels[-1]}"


def trouble(row):
    return bool(row and row["state"])


def nope(said):
    """A REFUSAL, MARKED. IMPORTED LATE, BECAUSE hands IMPORTS THIS PACKAGE."""
    from hands import reasons

    return reasons.no(said)


# NOTHING HERE CONNECTS OR SIGNS OUT: A BROWSER OPENING IN THE MIDDLE OF A SPOKEN
# ANSWER IS NOT AN ANSWER, AND THE PANEL ALREADY HAS THE BUTTON FOR BOTH.
TOOLS = [connections]
