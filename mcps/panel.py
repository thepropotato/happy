"""EVERY SERVICE AS ONE ROW, AND THE PANEL THOSE ROWS SIT IN.

A SERVICE IS NOT A SETTING AND IS NOT SHAPED LIKE ONE, BUT WHAT IS INSIDE ITS
ROW STILL IS: THE BOXES AND THE BUTTONS ARE ORDINARY KNOBS, SO THE WINDOW DRAWS
THEM WITH THE SAME CODE IT DRAWS EVERYTHING ELSE WITH.

WHAT IS CONNECTED COMES FIRST, WHAT IS NOT COMES NEXT, AND THE HANDFUL OF
SETTINGS NOBODY OPENS THIS PANEL TO MOVE IS FOLDED AWAY AT THE BOTTOM. THERE IS
NO ROW FOR ADDING A SERVER OF YOUR OWN ANY MORE, AND THAT IS THE POINT: THE LIST
IS EVERY SERVICE HAPPY SHIPS, AND NOTHING IN IT IS A PROGRAM NOBODY VETTED.

THERE IS NO SWITCH INSIDE A ROW EITHER. CONNECTED MEANS USED — A SERVICE SOMEBODY
WENT AND SIGNED INTO AND THEN LEFT SWITCHED OFF WAS A SERVICE THAT LOOKED PRESENT
AND ANSWERED NOTHING, AND SIGNING OUT IS ALREADY THE WAY TO STOP IT.
"""

from mcps import registry, tokens, wording
from memory.knobs import action, folded, heading, service, text

PASTE = "mcps.paste."

BEHAVE = "mcps.behave"

CONNECTED = "Connected"

COLD = "Not connected"

REST = "Rest"

BEHAVING = "How connections behave"

HELD = "Added — paste over it to change it"

# WHAT A SERVICE WANTS PASTED IN BEFORE IT CAN BE CONNECTED. THE SERVICE'S OWN
# NAME IS NOT IN THESE LABELS: THE BOX SITS INSIDE THAT SERVICE'S ROW ALREADY.
ASKED = {
    registry.TOKEN: [("token", "Token", "Kept in Happy's database, on this machine.")],
    registry.OAUTH: [
        # SIGNING INTO YOUR OWN UNVERIFIED APP STILL GETS THE RED SCREEN, AND
        # SOMEBODY UNWARNED READS IT AS HAPPY BEING THE UNSAFE PART.
        (
            "client",
            "Client ID",
            "It will warn that the app is unverified — it is yours. Open Advanced and carry on.",
        ),
        ("secret", "Client secret", "From the same one."),
    ],
}


def rows(behind=()):
    """EVERY SERVICE, CONNECTED ONES FIRST, AND THE RARELY TOUCHED AT THE END."""
    from mcps import store

    kept = {row["name"]: row for row in store.every()}
    live = []
    cold = []

    for known in registry.known():
        found = one(known, kept.get(known["name"]))
        (live if found["connected"] else cold).append(found)

    return sections(live, cold, behind)


def one(known, row):
    """ONE SERVICE: WHAT IT IS, HOW IT IS, AND WHATEVER IT IS STILL WAITING FOR."""
    name, kind, label = known["name"], known["kind"], known["label"]
    tools = doing(row)
    gone = wording.trouble(row)
    again = action(name, label, "connect", wording.asking(known), None)
    leaving = [action(name, f"{label} sign in", "disconnect", wording.SIGN_OUT, None)]

    # A SERVER STARTING IS NOT THE SAME AS A SERVICE BEING SIGNED INTO. WHATSAPP'S
    # OFFERS ALL TEN OF ITS TOOLS WITH NOBODY LINKED AT ALL, SO tools ON ITS OWN
    # SAID CONNECTED THE INSTANT SOMEBODY PRESSED THE BUTTON — MINUTES BEFORE THE
    # QR WAS SCANNED, AND FOREVER IF IT NEVER WAS.
    # ONE BUTTON, NEVER TWO. A ROW OFFERING BOTH A WAY IN AND A WAY OUT AT ONCE
    # ASKS SOMEBODY TO WORK OUT WHICH OF THEM THEY ARE, AND UNTIL THE QR IS
    # SCANNED THERE IS NOTHING SIGNED IN TO SIGN OUT OF.
    if tools and known.get("scan") and not scanned():
        return service(
            name,
            label,
            wording.initial(known),
            wording.plainly(gone) if gone else wording.WAITING,
            connected=False,
            note=wording.story(known, row),
            action=again,
        )

    if tools:
        # A SIGN IN THAT HAS DIED STILL HAS ITS TOOLS REMEMBERED, SO THE ROW STILL
        # OFFERS THE WAY BACK IN.
        return service(
            name,
            label,
            wording.initial(known),
            wording.plainly(gone) if gone else wording.said(len(tools)),
            tone="warn" if gone else "live",
            connected=True,
            signed=1,
            tools=len(tools),
            doing=tools,
            note=wording.story(known, row),
            action=again if gone else None,
            leaving=leaving,
        )

    return service(
        name,
        label,
        wording.initial(known),
        wording.wrong(known, row, poised(name, kind)),
        tone=wording.care(known, row),
        careful=bool(known.get("care")),
        ready=poised(name, kind),
        note=wording.story(known, row),
        fields=boxes(name, kind),
        action=again,
    )


def sections(live, cold, behind):
    drawn = []

    if live:
        drawn.append(heading(CONNECTED, tally(live)))
        drawn.extend(live)

    if cold:
        drawn.append(heading(COLD))
        drawn.extend(cold)

    drawn.append(heading(REST))
    drawn.append(folded(BEHAVE, BEHAVING, "⚙", list(behind)))

    return drawn


def tally(live):
    """WHAT THE Connected HEADING SAYS ON ITS RIGHT: HOW MANY, AND HOW MUCH."""
    tools = sum(each["tools"] for each in live)

    return f"{len(live)} · {wording.said(tools)}"


def boxes(name, kind):
    """THE PASTE FIELDS FOR ONE SERVICE, SAYING WHICH OF THEM IT ALREADY HAS."""
    return [
        text(f"{PASTE}{name}.{field}", label, "", hint, HELD if given(name, field) else "")
        for field, label, hint in ASKED.get(kind, [])
    ]


def given(name, field):
    """TRUE WHEN SOMETHING IS ALREADY KEPT FOR THIS BOX. NEVER WHAT IT IS."""
    try:
        if field == "token":
            return tokens.signed(name)

        held = tokens.client(name)
    except Exception:
        return False

    return bool(held.get("client_secret" if field == "secret" else "client_id"))


def poised(name, kind):
    """TRUE WHEN PRESSING CONNECT WOULD ACTUALLY GET SOMEWHERE."""
    try:
        return tokens.ready(name, kind)
    except Exception:
        return False


def scanned():
    """WHETHER THE ONE SERVICE WITH A QR HAS ACTUALLY HAD IT SCANNED.

    ASKED OF THE MODULE THAT ALREADY KNOWS RATHER THAN THE BRIDGE ITSELF: THIS
    RUNS ON EVERY DRAW OF THE PANEL, AND A ROUND TRIP PER DRAW WOULD BE FELT.
    """
    from mcps import whatsapp

    return whatsapp.linked()


def doing(row):
    """THE TOOL NAMES THIS SERVICE HANDS OVER, WHICH IS EVERYTHING ITS SERVER HAS."""
    if not row or not row["tools"]:
        return []

    return [each.get("name") for each in row["tools"] if each.get("name")]
