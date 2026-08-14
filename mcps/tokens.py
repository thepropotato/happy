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


def where():
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
        return signed(name)

    if kind == registry.OAUTH:
        return bool(client(name).get("client_id"))

    return True


def pasted(name, field, value):
    """SOMETHING TYPED INTO ONE OF A SERVICE'S BOXES, PUT WHERE THE REST LIVES."""
    value = (value or "").strip()

    if field == "token":
        put(name, tokens={"access_token": value, "token_type": "Bearer"})

        return

    held = client(name)
    held["client_id" if field == "client" else "client_secret"] = value

    put(name, client=held)
