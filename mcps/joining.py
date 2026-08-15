"""CHANGING WHAT IS CONNECTED: SIGNING IN, SWITCHING ON, PASTING SOMETHING IN."""

from mcps import bridging, pool, registry, store, tokens
from memory import settings


def connect(name):
    """CONNECT A SERVICE AND FIND OUT WHAT IT OFFERS. WAITS FOR A PERSON."""
    known = registry.find(name)

    if known is None:
        return f"There is nothing called {name}."

    if not tokens.ready(name, known["kind"]):
        return f"{known['label']} needs its details filled in first."

    if registry.signs_in(known["kind"]) and not tokens.signed(name):
        trouble = admitted(known)

        if trouble:
            return trouble

    row = store.one(name) or store.add(name)

    if not pool.refresh(row):
        return f"Could not reach {known['label']}. {store.one(name)['state'] or ''}".strip()

    stir()

    # WAITING FOR THE BRIDGE IS FINE HERE: CONNECTING HAS ITS OWN THREAD AND
    # NOBODY IS WAITING ON THIS ONE TO SPEAK.
    if known.get("scan"):
        if not bridging.scan():
            return f"Could not start {known['label']}. See data/whatsapp.log."

        return f"Scan the QR in your browser to finish linking {known['label']}."

    bridging.start()

    return f"{known['label']} is connected, with {len(store.one(name)['tools'])} tools."


def admitted(known):
    """THE BROWSER TRIP."""
    from mcps import oauth, permission

    name = known["name"]
    doorway = None

    store.add(name)

    try:
        doorway = permission.Doorway()
        oauth.sign_in(name, doorway)
    except Exception as error:
        store.mark(name, str(error)[:200])

        return f"Could not sign into {known['label']}. {str(error)[:150]}"
    finally:
        if doorway is not None:
            doorway.close()

    store.mark(name, None)

    return None


def disconnect(name):
    """FORGET THE SIGN IN AND SWITCH IT OFF."""
    if name == "whatsapp":
        bridging.disconnect(name)

    pool.drop(name)
    store.remember(name, [])
    store.mark(name, None)
    tokens.clear(name)
    stir()


def paste(where, value):
    """SOMETHING TYPED INTO ONE OF A SERVICE'S BOXES. where IS name.field."""
    name, _, field = str(where).partition(".")

    if not name or not field or registry.find(name) is None:
        return

    store.add(name)
    tokens.pasted(name, field, value)


def stir():
    """MOVE THE COUNTER THE GRAPH WATCHES."""
    settings.bump("mcps.servers")
