"""THE WORDS A CONNECTION'S ROW SAYS ABOUT IT, AND NOTHING ABOUT ITS SHAPE.

ONE LINE UNDER THE NAME, ONE WORD ON THE BUTTON. THE LONGER STORY IS ONLY EVER
READ BY SOMEBODY WHO OPENED THE ROW, WHICH IS WHY IT IS NOT IN THE LIST.
"""

from mcps import directory, filling

SIGN_OUT = "Sign out"

REMOVE = "Remove from the list"

SET_UP = "Set up"

CONNECT = "Connect"

SWITCH_ON = "Switch on"

MINE = "Added by you"

FIRST = "Add the client first"

READY = "Ready to sign in"

AGAIN = "Sign in again"

# WHAT THE SDK SAYS WHEN A SIGN IN HAS DIED. AN ORDINARY CONNECTION IS BUILT WITH
# NO WAY TO OPEN A BROWSER ON PURPOSE, SO A TOKEN THAT CANNOT BE REFRESHED COMES
# BACK AS THIS RATHER THAN AS A WINDOW IN FRONT OF WHOEVER IS STANDING THERE.
DIED = "no redirect handler"

# THE ONE LINE UNDER A SERVICE'S NAME. IT SAYS WHAT CONNECTING WILL COST AND
# NOTHING ELSE. A LIST WHERE EVERY LINE IS A PARAGRAPH IS A LIST NOBODY READS,
# WHICH IS THE SAME AS A LIST THAT SAYS NOTHING.
SAYS = {
    directory.OPEN: "Nothing to paste",
    directory.TOKEN: "Needs a token",
    directory.CLIENT: "Needs an app of your own",
    directory.LOCAL: "Runs on this machine",
}


def plainly(state):
    """A SERVER'S ERROR AS ONE LINE A PERSON CAN ACT ON. THE WHOLE OF IT IS STILL
    INSIDE THE ROW, WHERE SOMEBODY DEBUGGING WILL LOOK AND NOBODY ELSE WILL."""
    return AGAIN if DIED in (state or "").lower() else state


def wrong(known, row, fields):
    """THE LINE UNDER THE NAME: WHAT WENT WRONG, WHAT TO MIND, OR WHAT IT COSTS."""
    kind = known["kind"]

    if trouble(row):
        return plainly(trouble(row))

    if known.get("care"):
        return known["care"]

    # A MEMBER OF A FAMILY HAS NO BOXES OF ITS OWN, SO WHAT IT IS WAITING FOR IS
    # THE ONE CLIENT ITS FAMILY SHARES, A FEW LINES ABOVE IT.
    if not filling.poised(known["name"], kind):
        return SAYS.get(kind, CONNECT) if fields else FIRST

    return READY if directory.signs_in(kind) else SAYS.get(kind, CONNECT)


def story(known, row):
    """WHAT THE OPEN ROW SAYS. WHAT WENT WRONG COMES FIRST AND IN FULL: THE LINE IN
    THE LIST IS ONE LINE WIDE AND CUTS AN ERROR OFF EXACTLY WHERE IT MATTERS."""
    return " ".join(each for each in (ended(trouble(row)), known.get("hint")) if each) or None


def ended(said):
    """A SERVER'S OWN WORDS RARELY END IN A FULL STOP, AND WHAT FOLLOWS THEM RUNS
    STRAIGHT INTO THEM WHEN THEY DO NOT."""
    if not said:
        return None

    return said if said.endswith((".", "!", "?")) else said + "."


def pill(known, fields):
    """THE WORD ON THE RIGHT OF A ROW THAT IS NOT CONNECTED YET."""
    if fields and not filling.poised(known["name"], known["kind"]):
        return SET_UP

    return SWITCH_ON if known["kind"] == directory.LOCAL else CONNECT


def asking(known, label):
    """THE BUTTON ITSELF. IT NAMES THE SERVICE, BECAUSE IT IS THE LAST STEP."""
    if known["kind"] == directory.LOCAL:
        return SWITCH_ON

    if directory.signs_in(known["kind"]):
        return f"Sign into {label}"

    return f"{CONNECT} {label}"


def care(known, row):
    return "warn" if trouble(row) or known.get("care") else ""


def initial(known):
    return known.get("mark") or known["label"][:1].upper()


def said(count):
    return f"{count} tool" if count == 1 else f"{count} tools"


def listing(members):
    return ", ".join(each["label"] for each in members)


def trouble(row):
    return row["state"] if row else None
