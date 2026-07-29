"""ONE CONNECTION AS ONE ROW: WHAT IT IS, HOW IT IS, AND WHAT IT WANTS.

A SERVICE IS NOT A SETTING AND IS NOT SHAPED LIKE ONE. WHAT IS INSIDE THE ROW IS
STILL ORDINARY KNOBS, SO THE WINDOW DRAWS THE BOXES AND BUTTONS WITH THE SAME
CODE IT DRAWS EVERYTHING ELSE WITH.
"""

from mcps import directory, filling, wording
from memory.knobs import action, service

ON = "mcps.on."


def listed():
    """WHAT THE PANEL SHOWS: EVERY SERVICE, WITH THE ONES SHARING A SIGN IN AS ONE."""
    drawn = []
    done = set()

    for each in directory.known():
        family = each.get("family")

        if not family:
            drawn.append(each)
        elif family not in done:
            done.add(family)
            drawn.append({**directory.FAMILIES[family], "members": directory.household(family)})

    return drawn


def alone(known, row, compact=False):
    """ONE SERVICE. compact IS A MEMBER OF A FAMILY, DRAWN INSIDE ITS FAMILY'S ROW.

    A MEMBER GOES BY ITS SHORT NAME IN THERE. THE WORD GOOGLE IS ALREADY AT THE
    TOP OF THE ROW, AND SAYING IT AGAIN ON EVERY LINE UNDER IT READS AS THREE
    DIFFERENT GOOGLES RATHER THAN THREE PARTS OF THE ONE.
    """
    name, kind = known["name"], known["kind"]
    label = (known.get("short") or known["label"]) if compact else known["label"]
    tools = doing(row)

    if tools:
        # A SIGN IN THAT HAS DIED STILL HAS ITS TOOLS REMEMBERED, SO THE ROW OFFERS
        # THE WAY BACK IN. WITHOUT IT THE ONLY PATH IS SIGNING OUT OF SOMETHING THAT
        # IS ALREADY NOT WORKING, WHICH NOBODY WOULD GUESS AT.
        gone = wording.trouble(row)

        return service(
            name,
            label,
            wording.initial(known),
            wording.plainly(gone) if gone else wording.said(len(tools)),
            key=ON + name,
            tone="warn" if gone else ("live" if row["enabled"] else ""),
            connected=True,
            signed=1,
            tools=len(tools),
            doing=tools,
            note=wording.ended(gone) if compact else wording.story(known, row),
            action=action(name, label, "connect", wording.asking(known, label), None) if gone else None,
            leaving=[action(name, f"{label} sign in", "disconnect", wording.SIGN_OUT, None)],
        )

    wants = filling.wanted(known, compact)

    return service(
        name,
        label,
        wording.initial(known),
        wording.wrong(known, row, wants),
        tone=wording.care(known, row),
        careful=bool(known.get("care")),
        wording=wording.pill(known, wants),
        ready=filling.poised(name, kind),
        note=None if compact else wording.story(known, row),
        fields=wants,
        action=action(name, label, "connect", wording.asking(known, label), None),
    )


def household(known, kept):
    """A FAMILY: ONE ROW, ONE SETUP, AND ITS SERVICES AS SWITCHES INSIDE IT.

    THE BOXES ARE KEYED TO THE FIRST MEMBER BECAUSE THAT IS WHERE mcps.signing
    LOOKS: A CLIENT PASTED ONTO ONE SERVICE IS FOUND BY EVERY RELATIVE OF IT. THE
    FAMILY ITSELF IS NOT A CONNECTION AND HAS NOWHERE OF ITS OWN TO KEEP ONE.
    """
    members = [alone(each, kept.pop(each["name"], None), compact=True) for each in known["members"]]
    signed = [each for each in members if each["connected"]]
    eldest = known["members"][0]["name"]
    tools = sum(each["tools"] for each in signed)

    return service(
        known["name"],
        known["label"],
        wording.initial(known),
        f"{wording.listing(signed)} · {wording.said(tools)}" if signed else wording.listing(members),
        tone="live" if any(each["tone"] == "live" for each in signed) else "",
        connected=bool(signed),
        signed=len(signed),
        tools=tools,
        wording=wording.SET_UP,
        note=known.get("hint"),
        fields=filling.boxes(eldest, directory.CLIENT),
        parts=members,
    )


def mine(name, row):
    """A SERVER SOMEBODY PASTED IN. IT IS NOT IN THE DIRECTORY AND NEVER WILL BE.

    IT IS THE ONE KIND OF ROW THAT CAN LEAVE THE LIST ALTOGETHER, SO IT IS THE ONE
    KIND THAT OFFERS TO.
    """
    known = {"name": name, "label": row["label"], "kind": row["kind"], "hint": wording.MINE}
    drawn = alone(known, row)

    drawn["leaving"] += [action(name, row["label"], "forget", wording.REMOVE, None)]
    drawn["note"] = drawn["note"] or wording.MINE

    return drawn


def doing(row):
    """THE TOOLS THIS SERVICE ACTUALLY HANDS OVER, WHICH IS NOT ALWAYS ALL OF THEM."""
    if not row or not row["tools"]:
        return []

    from mcps import binding, cap, remembered

    try:
        kept = binding.wanted(remembered(row["tools"]), row["allowed"], cap())
    except Exception:
        return []

    return [each.name for each in kept]
