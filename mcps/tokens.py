"""WHAT A CONNECTED SERVICE LEFT BEHIND, AND WHAT THE PANEL DOES WITH IT.

EVERY TOKEN, EVERY PASTED SECRET AND EVERY OAUTH CLIENT SOMEBODY BROUGHT SITS IN
connection_secrets IN data/happy.db, UNENCRYPTED, AND NOWHERE ELSE. THE SYSTEM
KEYCHAIN WAS TRIED HERE AND TAKEN BACK OUT: WRITES FAILED SILENTLY FOR A PROCESS
NOBODY WAS SITTING IN FRONT OF, AND TWO ITEMS UNDER ONE NAME MEANT A READ AND A
WRITE COULD LAND ON DIFFERENT COPIES, SO A CONNECTION DISAGREED WITH ITSELF.

THE READING AND WRITING ITSELF BELONGS TO mcps/servers/shared/credentials.py,
WHICH IS THE ONE MODULE BOTH SIDES SHARE: THE SERVERS ARE THEIR OWN PROCESSES
AND LOOK THEIR OWN CREDENTIALS UP IN THE SAME TABLE THIS PANEL WRITES.
"""

from mcps import registry
from mcps.servers.shared import credentials


def kept(name):
    return credentials.kept(name)


def put(name, **moved):
    credentials.put(name, **moved)


def clear(name):
    """SIGN OUT. THE CLIENT SOMEBODY BROUGHT STAYS: THEY SPENT AN AFTERNOON ON IT,
    AND MAKING THEM FETCH IT AGAIN TO SIGN BACK IN IS NOT SIGNING OUT."""
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
    """SOMETHING TYPED INTO ONE OF A SERVICE'S BOXES, PUT WHERE THE REST LIVES.

    A CLIENT OF THEIR OWN GOES STRAIGHT INTO THE SLOT THE SIGN IN READS, WHICH IS
    WHAT LETS A SERVICE THAT WANTS AN APP TAKE THE SAME PATH AS ONE THAT DOES NOT.
    """
    value = (value or "").strip()

    if field == "token":
        put(name, tokens={"access_token": value, "token_type": "Bearer"})

        return

    held = client(name)
    held["client_id" if field == "client" else "client_secret"] = value

    put(name, client=held)
