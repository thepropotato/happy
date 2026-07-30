"""HOW A CONNECTION PROVES WHO IT IS: THE CLIENT IT SIGNS IN AS.

THE SIGN IN ITSELF LIVES IN mcps.granting. WHAT IS LEFT HERE IS THE PART A
PERSON TOUCHES — WHAT THEY PASTED IN, AND WHETHER THERE IS ENOUGH OF IT YET FOR
PRESSING CONNECT TO GET ANYWHERE.

NOTHING IN HERE ASKS WHICH SERVICE IT IS SPEAKING FOR. mcps.tokens ALREADY PUTS
A FAMILY'S ONE CLIENT UNDER THE FAMILY, SO GMAIL LOOKING FOR ITS CLIENT AND
DRIVE LOOKING FOR ITS CLIENT BOTH LAND ON GOOGLE'S.
"""

from mcps import directory, tokens


def client(name):
    """THE OAUTH CLIENT TO SIGN IN WITH, ITS OWN OR THE ONE ITS FAMILY SHARES."""
    return tokens.kept(name).get("client") or {}


def ready(name, kind):
    """TRUE WHEN THE SERVICE HAS EVERYTHING IT SAID IT NEEDED BEFORE SIGNING IN."""
    if kind == directory.TOKEN:
        return bool((tokens.kept(name).get("tokens") or {}).get("access_token"))

    if kind == directory.CLIENT:
        return bool(client(name).get("client_id"))

    return True


def pasted(name, field, value):
    """A TOKEN OR AN OAUTH CLIENT SOMEBODY TYPED IN, PUT WHERE THE REST LIVES.

    A CLIENT OF THEIR OWN IS WRITTEN STRAIGHT INTO THE SLOT REGISTERING WOULD
    HAVE FILLED, WHICH IS WHAT MAKES A SERVICE THAT REFUSES TO REGISTER HAPPY
    TAKE THE SAME PATH AS ONE THAT DOES.
    """
    value = (value or "").strip()

    if field == "token":
        tokens.put(name, tokens={"access_token": value, "token_type": "Bearer"})

        return

    held = client(name)
    held["client_id" if field == "client" else "client_secret"] = value

    tokens.put(name, client=held)
