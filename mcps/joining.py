"""CHANGING WHAT IS CONNECTED: SIGNING IN, SWITCHING ON, PASTING SOMETHING IN.

NOTHING HERE IS EVER REACHED BY A TOOL. SIGNING IN MEANS A BROWSER AND A PERSON
DECIDING SOMETHING, AND A WINDOW THAT APPEARS BECAUSE THE MODEL WANTED IT TO IS
NOT AN ANSWER TO ANYTHING SOMEBODY ASKED OUT LOUD.
"""

from mcps import binding, directory, loop, pool, store
from memory import settings


def fresh(name):
    """A ROW FOR A SERVICE HAPPY SHIPS WITH, THE FIRST TIME SOMEBODY WANTS IT."""
    known = directory.find(name)

    if known is None:
        return None

    store.save(name, known["label"], known["kind"], known["address"], known.get("allowed"))

    return store.one(name)


def connect(name):
    """SIGN INTO A SERVICE AND FIND OUT WHAT IT OFFERS. WAITS FOR A PERSON."""
    row = store.one(name) or fresh(name)

    if row is None:
        return f"There is nothing called {name}."

    from mcps import permission, signing

    if not signing.ready(name, row["kind"]):
        return f"{row['label']} needs its details filled in first."

    # A TOKEN OR A COMMAND IS NOT A SIGN IN. THERE IS NOBODY TO ASK ANYTHING, SO
    # IT ONLY HAS TO BE OPENED ONCE TO FIND OUT WHAT IT CAN DO.
    if not directory.signs_in(row["kind"]):
        if not pool.refresh(row):
            return f"Could not reach {row['label']}. {store.one(name)['state'] or ''}".strip()

        enable(name)

        return signed(store.one(name))

    return through(row, permission.Doorway())


def through(row, doorway):
    """THE WHOLE SIGN IN: A BROWSER, A WAIT, AND WHAT THE SERVICE OFFERS AFTER."""
    from mcps import permission, signing
    from mcps.session import Session, remote

    name = row["name"]

    try:
        here = Session(
            row["label"],
            remote(row["address"], auth=signing.openly(row, doorway)),
            timeout=permission.WAITING_SECONDS,
        )
        offered = loop.run(here.listing(), permission.WAITING_SECONDS + 30)
    except Exception as error:
        store.mark(name, str(error)[:200])

        return f"Could not sign into {row['label']}. {str(error)[:150]}"
    finally:
        doorway.close()

    store.remember(name, [each.model_dump() for each in offered])
    store.mark(name, None)
    loop.run(here.close(), 5)

    enable(name)

    return signed(store.one(name))


def signed(row):
    from mcps import remembered, cap

    kept = len(binding.wanted(remembered(row["tools"]), row["allowed"], cap()))

    return f"{row['label']} is connected, with {kept} tools."


def disconnect(name):
    """FORGET THE SIGN IN AND SWITCH IT OFF. THE CONNECTION ITSELF STAYS LISTED."""
    from mcps import tokens

    enable(name, False)
    tokens.clear(name)
    store.mark(name, None)


def enable(name, wanted=True):
    """SWITCH A CONNECTION ON OR OFF, AND LET THE GRAPH KNOW ITS TOOLS MOVED."""
    store.switch(name, wanted)

    if wanted:
        pool.warm()
    else:
        pool.drop(name)

    stir()


def add(name, label, kind, address, allowed=None):
    store.save(name, label, kind, address, allowed)
    stir()


def forget(name):
    pool.drop(name)
    store.forget(name)
    stir()


def custom(address):
    """A SERVER SOMEBODY PASTED IN. A WEB ADDRESS, OR A COMMAND ON THIS MACHINE."""
    address = (address or "").strip()

    if not address:
        return None

    elsewhere = address.startswith(("http://", "https://"))
    name = binding.tidy(calling(address, elsewhere))[:32]

    if not name:
        return None

    kind = directory.OPEN if elsewhere else directory.LOCAL
    add(name, name.replace("_", " ").title(), kind, address)

    return name


def calling(address, elsewhere):
    """WHAT TO CALL SOMETHING SOMEBODY PASTED IN, OUT OF THE ADDRESS ITSELF.

    THE HOST FOR A WEB ADDRESS. FOR A COMMAND IT IS THE LAST WORD, WHICH IS THE
    SERVER ITSELF RATHER THAN THE npx OR THE PYTHON THAT HAPPENS TO START IT.
    """
    if elsewhere:
        return address.split("/")[2].removeprefix("mcp.")

    last = address.split()[-1].split("/")[-1]

    return last.rsplit(".", 1)[0] or last


def paste(where, value):
    """SOMETHING TYPED INTO ONE OF A SERVICE'S BOXES. where IS name.field."""
    from mcps import signing

    name, _, field = str(where).partition(".")

    if not name or not field:
        return

    if store.one(name) is None:
        fresh(name)

    signing.pasted(name, field, value)


def stir():
    """MOVE THE COUNTER THE GRAPH WATCHES.

    A CONNECTION LIVES IN ITS OWN TABLE AND NOT IN settings, SO NOTHING WOULD
    OTHERWISE TELL brain/ THAT WHAT IT WAS BUILT OUT OF HAS CHANGED.
    """
    settings.bump("mcps.servers")
