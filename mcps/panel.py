"""EVERY SERVICE AS ONE ROW, AND THE PANEL THOSE ROWS SIT IN."""

from mcps import registry, tokens, wording
from memory.kinds import action, folded, heading, service, text

PASTE = "mcps.paste."

BEHAVE = "mcps.behave"

CONNECTED = "Connected"

COLD = "Not connected"

REST = "Rest"

BEHAVING = "How connections behave"

HELD = "Added — paste over it to change it"

# NO SERVICE NAME IN THESE LABELS: THE BOX SITS INSIDE THAT SERVICE'S ROW ALREADY.
ASKED = {
    registry.TOKEN: [("token", "Token", "Kept in Happy's database, on this machine.")],
    registry.OAUTH: [
        # UNWARNED, THE RED UNVERIFIED SCREEN READS AS HAPPY BEING THE UNSAFE PART.
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

    # A STARTED SERVER IS NOT A SIGNED IN SERVICE: WHATSAPP'S OFFERS EVERY TOOL
    # WITH NOBODY LINKED, SO tools ALONE WOULD SAY CONNECTED BEFORE THE QR.
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
        # A DEAD SIGN IN KEEPS ITS REMEMBERED TOOLS, SO THE ROW STILL OFFERS THE WAY BACK.
        return service(
            name,
            label,
            wording.initial(known),
            wording.plainly(gone) if gone else wording.numbered(len(tools)),
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
        fields=boxes(name, kind, known),
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

    return f"{len(live)} · {wording.numbered(tools)}"


def boxes(name, kind, known=None):
    """THE PASTE FIELDS FOR ONE SERVICE, SAYING WHICH OF THEM IT ALREADY HAS.

    A SERVICE MAY NAME ITS OWN IN wants: JIRA IS THE ONE THAT NEEDS SOMETHING BESIDES A
    TOKEN, BECAUSE ITS API LIVES AT A DIFFERENT ADDRESS FOR EVERY COMPANY."""
    asked = (known or {}).get("wants") or ASKED.get(kind, [])

    return [
        text(f"{PASTE}{name}.{field}", label, "", hint, HELD if given(name, field) else "")
        for field, label, hint in asked
    ]


def given(name, field):
    """TRUE WHEN SOMETHING IS ALREADY KEPT FOR THIS BOX. NEVER WHAT IT IS."""
    try:
        if field == "token":
            return tokens.signed(name)

        held = tokens.client(name)
    except Exception:
        return False

    if field == "secret":
        return bool(held.get("client_secret"))

    # ANYTHING ELSE A SERVICE ASKS FOR IS KEPT BESIDE THE CLIENT UNDER ITS OWN NAME.
    return bool(held.get("client_id" if field == "client" else field))


def poised(name, kind):
    """TRUE WHEN PRESSING CONNECT WOULD ACTUALLY GET SOMEWHERE."""
    try:
        return tokens.ready(name, kind)
    except Exception:
        return False


def scanned():
    """WHETHER THE ONE SERVICE WITH A QR HAS ACTUALLY HAD IT SCANNED."""
    from mcps import bridging

    return bridging.linked()


def doing(row):
    """THE TOOL NAMES THIS SERVICE HANDS OVER, WHICH IS EVERYTHING ITS SERVER HAS."""
    if not row or not row["tools"]:
        return []

    return [each.get("name") for each in row["tools"] if each.get("name")]
