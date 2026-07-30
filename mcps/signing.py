"""HOW A CONNECTION PROVES WHO IT IS. NEXT DOOR KEEPS WHAT COMES BACK.

SIGNING IN AND STAYING SIGNED IN ARE DELIBERATELY DIFFERENT THINGS HERE. AN
ORDINARY CONNECTION IS BUILT WITH NO WAY TO OPEN A BROWSER AT ALL, SO A TOKEN
THAT HAS DIED COMES BACK AS AN ERROR SOMEBODY CAN BE TOLD ABOUT RATHER THAN AS A
WINDOW APPEARING IN FRONT OF WHOEVER IS STANDING THERE MID SENTENCE.
"""

from mcp.client.auth import OAuthClientProvider
from mcp.shared.auth import OAuthClientMetadata

from mcps import directory, tokens
from mcps.tokens import UNUSED, Keeping


def client(name):
    """THE OAUTH CLIENT TO SIGN IN WITH, ITS OWN OR A RELATIVE'S.

    ONE GOOGLE CLOUD PROJECT COVERS MAIL, CALENDAR AND DRIVE, SO ASKING FOR THE
    SAME CLIENT THREE TIMES WOULD BE THE SAME ERRAND THREE TIMES. THE TOKENS STAY
    SEPARATE: ONLY THE CLIENT IS SHARED, AND EACH SERVICE IS SIGNED INTO ALONE.
    """
    held = tokens.kept(name).get("client") or {}

    if held.get("client_id"):
        return held

    for other in directory.relatives(name):
        theirs = tokens.kept(other).get("client") or {}

        if theirs.get("client_id"):
            return theirs

    return {}


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

    held = tokens.kept(name).get("client") or {}
    held["client_id" if field == "client" else "client_secret"] = value
    held.setdefault("redirect_uris", [UNUSED])

    tokens.put(name, client=held)


def about(name, redirect):
    """WHAT HAPPY TELLS A SERVICE IT IS, WHEN THE SERVICE WILL REGISTER IT."""
    known = directory.find(name) or {}
    scopes = known.get("scopes") or []

    # AN OAUTH CLIENT USUALLY COMES WITH A SECRET, AND SAYING THERE IS NONE WOULD
    # HAVE THE TOKEN REQUEST TURNED AWAY.
    secret = client(name).get("client_secret")

    return OAuthClientMetadata(
        redirect_uris=[redirect],
        grant_types=["authorization_code", "refresh_token"],
        scope=" ".join(scopes) or None,
        client_name="Happy",
        token_endpoint_auth_method="client_secret_post" if secret else "none",
    )


def quietly(row):
    """THE SIGN IN AN ORDINARY CONNECTION CARRIES: REFRESH ONLY, NEVER A BROWSER.

    NO HANDLERS MEANS THE PROTOCOL RAISES RATHER THAN TRYING TO ASK SOMEBODY
    SOMETHING, WHICH IS THE WHOLE POINT.
    """
    return OAuthClientProvider(
        server_url=row["address"],
        client_metadata=about(row["name"], UNUSED),
        storage=Keeping(row["name"]),
    )


def openly(row, doorway):
    """THE SIGN IN A PERSON ASKED FOR, WITH A REAL DOOR TO COME BACK THROUGH."""
    return OAuthClientProvider(
        server_url=row["address"],
        client_metadata=about(row["name"], doorway.address),
        storage=Keeping(row["name"]),
        redirect_handler=doorway.opening,
        callback_handler=doorway.landed,
    )
