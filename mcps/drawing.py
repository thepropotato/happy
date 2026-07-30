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

    # A MEMBER OF A FAMILY OFFERS NEITHER A WAY IN NOR A WAY OUT. BOTH BELONG TO
    # THE ONE SIGN IN ALL OF THEM SHARE.
    again = None if compact else action(name, label, "connect", wording.asking(known, label), None)

    if tools:
        # A SIGN IN THAT HAS DIED STILL HAS ITS TOOLS REMEMBERED, SO THE ROW STILL
        # OFFERS THE WAY BACK IN.
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
            action=again if gone else None,
            leaving=[] if compact else [
                action(name, f"{label} sign in", "disconnect", wording.SIGN_OUT, None)
            ],
        )

    wants = filling.wanted(known, compact)

    return service(
        name,
        label,
        wording.initial(known),
        wording.wrong(known, row, wants),
        tone=wording.care(known, row),
        careful=bool(known.get("care")),
        ready=filling.poised(name, kind),
        note=None if compact else wording.story(known, row),
        fields=wants,
        action=again,
    )


def household(known, kept):
    """A FAMILY: ONE ROW, ONE SETUP, ONE SIGN IN, AND ITS SERVICES INSIDE IT.

    THE CLIENT AND THE TOKEN ARE KEPT UNDER THE FAMILY'S OWN NAME, SO THE BOXES
    AND THE BUTTON ARE KEYED TO IT TOO. PRESSING IT ONCE SIGNS INTO ALL OF THEM:
    ONE GOOGLE ACCOUNT AGREEING TO MAIL, CALENDAR AND DRIVE IS ONE QUESTION, AND
    ASKING IT THREE TIMES WAS WHERE PEOPLE PUT THE PANEL DOWN.
    """
    name, label = known["name"], known["label"]
    members = [alone(each, kept.pop(each["name"], None), compact=True) for each in known["members"]]
    signed = [each for each in members if each["connected"]]
    tools = sum(each["tools"] for each in signed)

    return service(
        name,
        label,
        wording.initial(known),
        f"{wording.listing(signed)} · {wording.said(tools)}" if signed else wording.listing(members),
        tone="live" if any(each["tone"] == "live" for each in signed) else "",
        connected=bool(signed),
        signed=len(signed),
        tools=tools,
        ready=filling.poised(name, known["kind"]),
        note=known.get("hint"),
        fields=filling.boxes(name, directory.CLIENT),
        parts=members,
        action=action(name, label, "connect", f"Sign into {label}", None),
        leaving=[action(name, f"{label} sign in", "disconnect", wording.SIGN_OUT, None)]
        if signed
        else [],
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
