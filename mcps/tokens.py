"""WHAT A SIGNED IN SERVICE LEFT BEHIND, AND WHERE IT IS PUT.

EVERY TOKEN, EVERY PASTED SECRET AND EVERY CLIENT SOMEBODY BROUGHT SITS IN
connection_secrets IN data/happy.db, UNENCRYPTED, AND NOWHERE ELSE. THE SYSTEM
KEYCHAIN WAS TRIED HERE AND TAKEN BACK OUT: WRITES FAILED SILENTLY FOR A PROCESS
NOBODY WAS SITTING IN FRONT OF, AND TWO ITEMS UNDER ONE NAME MEANT A READ AND A
WRITE COULD LAND ON DIFFERENT COPIES, SO A CONNECTION'S STATE DISAGREED WITH
ITSELF. ONE STORE HAPPY CAN SEE BEATS A SAFER ONE IT CANNOT.

A SIGN IN IS KEPT UNDER WHOEVER OWNS IT, NOT UNDER WHOEVER USES IT. MAIL,
CALENDAR AND DRIVE ARE ONE GOOGLE ACCOUNT SAYING YES ONCE, SO ALL THREE READ AND
WRITE THE ONE ROW AND NOBODY IS ASKED THE SAME QUESTION THREE TIMES.
"""

from mcps import directory, store


def holder(name):
    """WHOSE SIGN IN THIS SERVICE USES: ITS FAMILY'S, OR ITS OWN."""
    return (directory.find(name) or {}).get("family") or name


def where():
    """WHAT A PERSON SHOULD BE TOLD THEIR SIGN IN IS SITTING IN."""
    return "Happy's database, unencrypted"


def kept(name):
    return store.secret(holder(name)) or {}


def put(name, **moved):
    held = kept(name)
    held.update(moved)

    store.keep(
        holder(name),
        tokens=held.get("tokens"),
        client=held.get("client"),
        auth=held.get("auth"),
    )


def clear(name):
    """SIGN OUT. THE CLIENT SOMEBODY BROUGHT STAYS: THEY SPENT AN AFTERNOON ON IT,
    AND MAKING THEM FETCH IT AGAIN TO SIGN BACK IN IS NOT SIGNING OUT."""
    put(name, tokens=None)
