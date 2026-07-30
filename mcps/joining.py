"""CHANGING WHAT IS CONNECTED: SIGNING IN, SWITCHING ON, PASTING SOMETHING IN.

NOTHING HERE IS EVER REACHED BY A TOOL. SIGNING IN MEANS A BROWSER AND A PERSON
DECIDING SOMETHING, AND A WINDOW THAT APPEARS BECAUSE THE MODEL WANTED IT TO IS
NOT AN ANSWER TO ANYTHING SOMEBODY ASKED OUT LOUD.
"""

from mcps import binding, directory, pool, store
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
    if name in directory.FAMILIES:
        return whole(name)

    from mcps import granting, signing

    row = store.one(name) or fresh(name)

    if row is None:
        return f"There is nothing called {name}."

    if not signing.ready(name, row["kind"]):
        return f"{row['label']} needs its details filled in first."

    # A TOKEN OR A COMMAND IS NOT A SIGN IN: THERE IS NOBODY TO ASK ANYTHING, SO
    # IT ONLY HAS TO BE OPENED ONCE TO FIND OUT WHAT IT CAN DO.
    if directory.signs_in(row["kind"]) and not granting.signed(name):
        trouble = admitted(row)

        if trouble:
            return trouble

    if not pool.refresh(row):
        return f"Could not reach {row['label']}. {store.one(name)['state'] or ''}".strip()

    enable(name)

    return signed(store.one(name))


def whole(family):
    """ONE SIGN IN, THEN EVERY SERVICE IT COVERS. THE WHOLE POINT OF A FAMILY.

    THE CONSENT ASKS FOR WHAT ALL OF THEM NEED AT ONCE, SO ONE GOOGLE ACCOUNT IS
    ONE TRIP THROUGH ONE SCREEN RATHER THAN THE SAME ERRAND THREE TIMES.
    """
    from mcps import granting, signing

    known = directory.FAMILIES[family]
    kin = [store.one(each["name"]) or fresh(each["name"]) for each in directory.household(family)]
    kin = [row for row in kin if row]

    if not kin:
        return f"There is nothing called {family}."

    if not signing.ready(family, known["kind"]):
        return f"{known['label']} needs its details filled in first."

    if not granting.signed(family):
        trouble = admitted(kin[0], known["label"])

        if trouble:
            return trouble

    opened = []

    for row in kin:
        if pool.refresh(row):
            enable(row["name"])
            opened.append(store.one(row["name"]))

    if not opened:
        return f"Signed into {known['label']}, but nothing answered."

    return f"{known['label']} is connected, with {sum(counted(row) for row in opened)} tools."


def admitted(row, label=None):
    """THE BROWSER TRIP. NOTHING WHEN IT WORKED, THE REASON WHEN IT DID NOT.

    THE SIGN IN IS ITS OWN STEP RATHER THAN SOMETHING THE FIRST REFUSED REQUEST
    SETS OFF: GOOGLE'S SERVERS HAND OVER THEIR TOOL LIST WITHOUT ASKING WHO IS
    CALLING AND ONLY REFUSE LATER, SO NOTHING WOULD EVER HAVE SET IT OFF.
    """
    from mcps import granting, permission

    label = label or row["label"]
    doorway = None

    try:
        doorway = permission.Doorway()
        granting.sign_in(row, doorway)
    except Exception as error:
        store.mark(row["name"], str(error)[:200])

        return f"Could not sign into {label}. {str(error)[:150]}"
    finally:
        if doorway is not None:
            doorway.close()

    store.mark(row["name"], None)

    # WHATEVER WAS ALREADY OPEN SHOOK HANDS AS A STRANGER, SO IT IS DROPPED.
    for each in [row["name"], *directory.relatives(row["name"])]:
        pool.drop(each)

    return None


def signed(row):
    return f"{row['label']} is connected, with {counted(row)} tools."


def counted(row):
    """HOW MANY OF WHAT THIS SERVER OFFERS THE MODEL WILL ACTUALLY BE HANDED."""
    from mcps import cap, remembered

    return len(binding.wanted(remembered(row["tools"]), row["allowed"], cap()))


def disconnect(name):
    """FORGET THE SIGN IN AND SWITCH IT OFF. THE CONNECTION ITSELF STAYS LISTED."""
    from mcps import tokens

    if name in directory.FAMILIES:
        for each in directory.household(name):
            enable(each["name"], False)
            store.mark(each["name"], None)

        tokens.clear(name)

        return

    enable(name, False)
    store.mark(name, None)

    # A SHARED SIGN IN IS NOT ONE SERVICE'S TO THROW AWAY: SIGNING OUT OF MAIL
    # MUST NOT SIGN SOMEBODY OUT OF THE CALENDAR THEY LEFT SWITCHED ON.
    if not any(still(each) for each in directory.relatives(name)):
        tokens.clear(name)


def still(name):
    row = store.one(name)

    return bool(row and row["enabled"])


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

    if name not in directory.FAMILIES and store.one(name) is None:
        fresh(name)

    signing.pasted(name, field, value)


def stir():
    """MOVE THE COUNTER THE GRAPH WATCHES.

    A CONNECTION LIVES IN ITS OWN TABLE AND NOT IN settings, SO NOTHING WOULD
    OTHERWISE TELL brain/ THAT WHAT IT WAS BUILT OUT OF HAS CHANGED.
    """
    settings.bump("mcps.servers")
