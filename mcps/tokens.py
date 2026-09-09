"""WHAT A CONNECTED SERVICE LEFT BEHIND, AND WHAT THE PANEL DOES WITH IT."""

from mcps import registry
from mcps.servers.shared import credentials


def kept(name):
    return credentials.kept(name)


def put(name, **moved):
    credentials.put(name, **moved)


def clear(name):
    """SIGN OUT."""
    credentials.clear(name)


def sitting():
    """WHAT A PERSON SHOULD BE TOLD THEIR SIGN IN IS SITTING IN."""
    return "Happy's database, unencrypted"


def client(name):
    """THE OAUTH CLIENT THIS SERVICE SIGNS IN AS, WHEN IT NEEDS ONE OF ITS OWN."""
    return kept(name)["client"]


def signed(name):
    """TRUE WHEN THIS SERVICE HAS SOMETHING TO REACH ITS SERVICE WITH."""
    held = kept(name)["tokens"]

    return bool(held.get("access_token") or held.get("refresh_token"))


def ready(name, kind):
    """TRUE WHEN PRESSING CONNECT WOULD ACTUALLY GET SOMEWHERE."""
    if kind == registry.TOKEN:
        # A SERVICE THAT ASKED FOR MORE THAN A TOKEN NEEDS ALL OF IT: JIRA WITH ONLY THE
        # TOKEN IN WOULD LIGHT UP CONNECT AND THEN FAIL ON THE SITE IT WAS NEVER GIVEN.
        return signed(name) and all(filled(name, field) for field in besides(name))

    if kind == registry.OAUTH:
        return bool(client(name).get("client_id"))

    return True


def besides(name):
    """THE BOXES THIS SERVICE ASKED FOR THAT ARE NOT THE TOKEN ITSELF."""
    known = registry.one(name) or {}

    return [field for field, *_ in known.get("wants") or [] if field != "token"]


def filled(name, field):
    """TRUE WHEN ONE OF THOSE HAS SOMETHING IN IT. NEVER WHAT."""
    try:
        return bool(str(client(name).get(field) or "").strip())
    except Exception:
        return False


def pasted(name, field, value):
    """SOMETHING TYPED INTO ONE OF A SERVICE'S BOXES, PUT WHERE THE REST LIVES."""
    value = (value or "").strip()

    if field == "token":
        put(name, tokens={"access_token": value, "token_type": "Bearer"})

        return

    held = client(name)

    # THE TWO OAUTH BOXES HAVE THE NAMES OAUTH GAVE THEM; ANYTHING ELSE A SERVICE ASKS FOR
    # IS KEPT BESIDE THEM UNDER THE NAME THAT SERVICE USED — JIRA'S site AND email.
    if field in ("client", "secret"):
        held["client_id" if field == "client" else "client_secret"] = value
    else:
        held[field] = value

    put(name, client=held)
