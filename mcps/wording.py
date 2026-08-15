"""THE WORDS A SERVICE'S ROW SAYS ABOUT IT, AND NOTHING ABOUT ITS SHAPE."""

from mcps import registry

SIGN_OUT = "Sign out"

CONNECT = "Connect"

FIRST = "Add the app first"

READY = "Ready to sign in"

AGAIN = "Sign in again"

WAITING = "Waiting for the QR to be scanned"

# A SERVER NEVER OPENS A BROWSER, ON PURPOSE, SO A TOKEN THAT CANNOT BE RENEWED
# COMES BACK AS THE SERVICE REFUSING.
DIED = ("401", "unauthorized", "invalid_grant", "not signed in", "not connected")

# THE ONE LINE UNDER A SERVICE'S NAME: WHAT CONNECTING COSTS, AND NOTHING ELSE.
SAYS = {
    registry.NONE: "Runs on this machine",
    registry.TOKEN: "Needs a token",
    registry.OAUTH: "Needs an app of your own",
}


def plainly(state):
    """A SERVER'S ERROR AS ONE LINE A PERSON CAN ACT ON."""
    said = (state or "").lower()

    return AGAIN if any(each in said for each in DIED) else state


def wrong(known, row, poised):
    """THE LINE UNDER THE NAME: WHAT WENT WRONG, WHAT TO MIND, OR WHAT IT COSTS."""
    kind = known["kind"]

    if trouble(row):
        return plainly(trouble(row))

    if known.get("care"):
        return known["care"]

    if not poised:
        return SAYS.get(kind, CONNECT)

    return READY if registry.signs_in(kind) else SAYS.get(kind, CONNECT)


def story(known, row):
    """WHAT THE OPEN ROW SAYS."""
    return " ".join(each for each in (ended(trouble(row)), known.get("hint")) if each) or None


def ended(said):
    """A SERVER'S OWN WORDS RARELY END IN A FULL STOP, AND WHAT FOLLOWS THEM RUNS STRAIGHT INTO
    THEM WHEN THEY DO NOT."""
    if not said:
        return None

    return said if said.endswith((".", "!", "?")) else said + "."


def asking(known):
    """THE BUTTON ITSELF."""
    if registry.signs_in(known["kind"]):
        return f"Sign into {known['label']}"

    return f"{CONNECT} {known['label']}"


def care(known, row):
    return "warn" if trouble(row) or known.get("care") else ""


def initial(known):
    return known.get("mark") or known["label"][:1].upper()


def numbered(count):
    return f"{count} tool" if count == 1 else f"{count} tools"


def trouble(row):
    return row["state"] if row else None
