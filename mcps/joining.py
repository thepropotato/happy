"""CHANGING WHAT IS CONNECTED: SIGNING IN, SWITCHING ON, PASTING SOMETHING IN.

NOTHING HERE IS EVER REACHED BY A TOOL. SIGNING IN MEANS A BROWSER AND A PERSON
DECIDING SOMETHING, AND A WINDOW THAT APPEARS BECAUSE THE MODEL WANTED IT TO IS
NOT AN ANSWER TO ANYTHING SOMEBODY ASKED OUT LOUD.

THERE IS NO WAY TO ADD A SERVICE FROM OUT HERE ANY MORE. THE LIST IS WHATEVER
mcps/registry.py SAYS IT IS, AND ADDING TO IT MEANS WRITING A SERVER.
"""

from mcps import pool, registry, store, tokens, whatsapp
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

    # A SERVICE THAT STILL WANTS SCANNING FINISHES IN A BROWSER, THE WAY SIGNING
    # INTO GOOGLE ALREADY DOES. WAITING FOR THE BRIDGE HERE IS FINE: CONNECTING
    # RUNS ON ITS OWN THREAD AND NOBODY IS WAITING ON THIS ONE TO SPEAK.
    if known.get("scan"):
        if not whatsapp.scan():
            return f"Could not start {known['label']}. See data/whatsapp.log."

        return f"Scan the QR in your browser to finish linking {known['label']}."

    whatsapp.start()

    return f"{known['label']} is connected, with {len(store.one(name)['tools'])} tools."


def admitted(known):
    """THE BROWSER TRIP. NOTHING WHEN IT WORKED, THE REASON WHEN IT DID NOT.

    THE SIGN IN IS ITS OWN STEP RATHER THAN SOMETHING THE FIRST REFUSED REQUEST
    SETS OFF: A SERVER HANDS OVER ITS TOOL LIST WITHOUT ASKING WHO IS CALLING
    AND ONLY REFUSES LATER, SO NOTHING WOULD EVER HAVE SET IT OFF.
    """
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
    """FORGET THE SIGN IN AND SWITCH IT OFF. THE SERVICE ITSELF STAYS LISTED.

    WHAT THE SERVER OFFERED IS FORGOTTEN TOO, AND THAT IS THE WHOLE OF SIGNING
    OUT AS FAR AS THE PANEL IS CONCERNED: A ROW IS DRAWN AS CONNECTED BECAUSE IT
    REMEMBERS TOOLS, SO A SIGN OUT THAT LEFT THEM SITTING THERE CHANGED NOTHING
    ANYBODY COULD SEE — SAME HEADING, SAME COUNT, NO WAY BACK IN.
    """
    if name == "whatsapp":
        whatsapp.disconnect(name)

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
    """MOVE THE COUNTER THE GRAPH WATCHES.

    A CONNECTION LIVES IN ITS OWN TABLE AND NOT IN settings, SO NOTHING WOULD
    OTHERWISE TELL brain/ THAT WHAT IT WAS BUILT OUT OF HAS CHANGED.
    """
    settings.bump("mcps.servers")
