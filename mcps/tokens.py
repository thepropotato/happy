"""WHAT A SIGNED IN SERVICE LEFT BEHIND, AND WHERE IT IS PUT.

THE DATABASE ALREADY HOLDS EVERY WORD EVER SAID, SO A REFRESH TOKEN IN IT IS NOT
A NEW WAY TO BE EXPOSED — BUT IT IS A FAR WORSE CONSEQUENCE OF THE SAME ONE, AS
THE FILE NOW READS YOUR MAIL. SO THE SYSTEM KEYCHAIN IS USED WHEN THERE IS ONE
AND THE TABLE WHEN THERE IS NOT, AND where() SAYS WHICH SO THE PANEL CAN TOO.
"""

import json

from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from mcps import store

SAFE = "happy-mcps"

UNUSED = "http://127.0.0.1:0/callback"  # NEVER VISITED. A CLIENT METADATA NEEDS ONE.


def chest():
    """THE SYSTEM KEYCHAIN, IF THIS MACHINE HAS ONE WE CAN ACTUALLY USE."""
    try:
        import keyring

        keyring.get_keyring()

        return keyring
    except Exception:
        return None


def where():
    """WHAT A PERSON SHOULD BE TOLD THEIR SIGN IN IS SITTING IN."""
    return "the system keychain" if chest() else "Happy's database, unencrypted"


def kept(name):
    safe = chest()

    if safe:
        try:
            held = safe.get_password(SAFE, name)

            if held:
                return json.loads(held)
        except Exception:  # A KEYCHAIN THAT WILL NOT OPEN IS THE SAME AS NOT HAVING ONE.
            pass

    return store.secret(name) or {}


def put(name, **moved):
    held = kept(name)
    held.update(moved)

    safe = chest()

    if safe:
        try:
            safe.set_password(SAFE, name, json.dumps(held))

            return
        except Exception:
            pass

    store.keep(name, tokens=held.get("tokens"), client=held.get("client"))


def clear(name):
    safe = chest()

    if safe:
        try:
            safe.delete_password(SAFE, name)
        except Exception:
            pass

    store.keep(name, tokens=None, client=None)


class Keeping:
    """ONE CONNECTION'S SIGN IN, IN THE SHAPE THE PROTOCOL WANTS TO READ IT."""

    def __init__(self, name):
        self.name = name

    async def get_tokens(self):
        return shaped(OAuthToken, kept(self.name).get("tokens"))

    async def set_tokens(self, tokens):
        put(self.name, tokens=tokens.model_dump(mode="json", exclude_none=True))

    async def get_client_info(self):
        from mcps import signing

        held = signing.client(self.name)

        # A CLIENT TYPED IN BY HAND CARRIES NO REDIRECT, AND THE SHAPE INSISTS ON
        # ONE. THE ONE ACTUALLY USED COMES OFF THE LIVE DOOR, NOT OFF THIS.
        if held:
            held.setdefault("redirect_uris", [UNUSED])

        return shaped(OAuthClientInformationFull, held)

    async def set_client_info(self, client_info):
        put(self.name, client=client_info.model_dump(mode="json", exclude_none=True))


def shaped(kind, held):
    if not held:
        return None

    try:
        return kind(**held)
    except Exception:  # SOMETHING SAVED BY AN OLDER HAPPY. SIGN IN AGAIN, DO NOT CRASH.
        return None
