"""A ROUTINE TAKEN OFF A TURN THAT ALREADY WORKED, RATHER THAN ONE IMAGINED."""

import re

from memory import conversation

# HOW MANY EXCHANGES BACK save_routine WILL EVER REACH, WHATEVER IT IS ASKED FOR.
FURTHEST = 6

# A WHOLE PAGE CAME BACK FROM SOME OF THESE. AN EXAMPLE ONLY HAS TO SHOW THE SHAPE.
SHOWN = 200

ELLIPSIS = "..."

# SHORTER THAN THIS AND MATCHING IT AGAINST WHAT A TOOL SAID MEANS NOTHING: EVERY RESULT
# LONG ENOUGH TO BE USEFUL HOLDS "true" AND "id" AND "mail" SOMEWHERE IN IT.
OPAQUE = 6

SPLIT = re.compile(r"[^A-Za-z0-9]+")

# THE TOOLS THAT MAKE AND RUN ROUTINES NEVER BELONG INSIDE ONE.
OURS = {"routine"}


def behind(turns=1, without=None):
    """THE EXCHANGES A ROUTINE IS MADE OF, WORKED OUT RATHER THAN TAKEN ON TRUST."""
    kept = finished(without)

    if not kept:
        return []

    wanted = max(1, min(int(turns or 1), FURTHEST))

    return kept[widened(kept, max(0, len(kept) - wanted)):]


def widened(kept, start):
    """HOW FAR BACK THE JOB REALLY BEGAN, AND NOT WHERE SOMEBODY HAPPENED TO STOP TALKING.

    A PERSON TALKS THEIR WAY INTO A JOB: WHAT IS UNREAD, AND THEN MORE ABOUT THAT ONE. THE
    LAST THING SAID IS ONLY THE SECOND HALF, AND SAVED ON ITS OWN IT READS AN EMAIL BY AN ID
    THAT NOTHING IN IT EVER FINDS. SO THE ARGUMENTS ARE THE TEST, NOT THE WORDING: A VALUE
    HANDED TO A TOOL THAT CAME OUT OF A TOOL FURTHER BACK, RATHER THAN OUT OF THIS STRETCH
    OR OUT OF THE PERSON'S OWN MOUTH, PULLS THAT TURN IN TOO. WHERE NOTHING DANGLES THE JOB
    STARTS HERE, WHICH IS WHY THIS STOPS ON ITS OWN RATHER THAN WALKING BACK FOR EVER."""
    while start > 0 and len(kept) - start < FURTHEST:
        wanted = dangling(kept[start:])

        if not wanted or not any(each in produced(kept[start - 1]) for each in wanted):
            break

        start -= 1

    return start


def dangling(span):
    """WHAT THE SPAN HANDS ITS TOOLS THAT IT NEVER WENT AND GOT FOR ITSELF."""
    said = " ".join(each.get("message") or "" for each in span)
    wanted = set()
    already = ""

    for exchange in span:
        for call in exchange.get("tools") or []:
            for value in inside(call.get("args")):
                wanted.update(each for each in pieces(value)
                              if each not in said and each not in already)

            # AFTER, NOT BEFORE: A CALL CANNOT HAVE BEEN GIVEN WHAT IT IS ABOUT TO RETURN.
            already += " " + str(call.get("result") or "")

    return wanted


def pieces(value):
    """A VALUE AND THE PARTS OF IT WORTH LOOKING FOR.

    AN ARGUMENT IS OFTEN BUILT OUT OF TWO EARLIER ANSWERS RATHER THAN COPIED FROM ONE — A
    FOLDER FROM THE SEARCH AND A FILENAME FROM THE LISTING, JOINED INTO A PATH THAT APPEARS
    NOWHERE BEFORE IT. SO THE PARTS ARE LOOKED FOR TOO, AND WHERE THAT DRAGS IN A TURN THAT
    WAS NOT NEEDED THE ROUTINE ONLY DOES A LITTLE MORE THAN IT HAD TO. THE OTHER MISTAKE
    LEAVES IT UNABLE TO RUN AT ALL, AND IS THE ONE WORTH LEANING AWAY FROM."""
    found = {value}

    found.update(each for each in SPLIT.split(value) if len(each) >= OPAQUE)

    return found


def produced(exchange):
    """EVERYTHING ONE EXCHANGE'S TOOLS SAID, AS ONE STRING TO LOOK IN."""
    return " ".join(str(call.get("result") or "") for call in exchange.get("tools") or [])


def inside(args):
    """EVERY STRING BURIED ANYWHERE IN A CALL'S ARGUMENTS, LONG ENOUGH TO MEAN SOMETHING."""
    if isinstance(args, str):
        return [args] if len(args) >= OPAQUE else []

    if isinstance(args, dict):
        return [each for value in args.values() for each in inside(value)]

    if isinstance(args, (list, tuple)):
        return [each for value in args for each in inside(value)]

    return []


def finished(without=None):
    """THE LAST FEW FINISHED EXCHANGES, OLDEST FIRST, THE ONE IN PROGRESS LEFT OUT."""
    here = conversation.here.get() if without is None else without

    return [each for each in conversation.history(FURTHEST + 2)
            if each.get("id") != here and each.get("reply")]


def off(exchanges):
    """WHAT A ROUTINE CAN BE MADE OF: THE CALLS THAT WORKED, IN THE ORDER THEY WORKED."""
    calls = [call for each in exchanges for call in each.get("tools") or []
             if not call.get("failed") and call.get("name") not in OURS]

    return {
        "tools": sorted({call["name"] for call in calls}),
        "examples": [shown(call) for call in calls],
        "steps": written(calls),
        "asked": [each.get("message") for each in exchanges if each.get("message")],
    }


def shown(call):
    """ONE CALL AS THE MODEL WILL READ IT BACK: WHAT WENT IN AND WHAT CAME OUT."""
    return {
        "name": call["name"],
        "args": call.get("args") or {},
        "result": clipped(call.get("result")),
    }


def written(calls):
    """THE STEPS, IN THE WORDS HAPPY USED AT THE TIME.

    EVERY TOOL CALL ALREADY CARRIES THE ONE OR TWO SENTENCES SAYING WHAT IT WAS DOING AND
    WHY, BECAUSE EVERY TOOL IS MADE TO ASK FOR THEM. THAT IS A STEP LIST NOBODY HAS TO
    WRITE, AND IT IS THE ONLY ONE DESCRIBING A RUN THAT ACTUALLY HAPPENED."""
    lines = []

    for call in calls:
        said = (call.get("why") or "").strip()
        step = f"- {said} ${{TOOL: {call['name']}}}" if said else f"- Call ${{TOOL: {call['name']}}}"

        # THE SAME TOOL FOR THE SAME REASON TWICE RUNNING IS ONE STEP SAID TWICE.
        if step not in lines[-1:]:
            lines.append(step)

    return "\n".join(lines)


def clipped(said):
    text = "" if said is None else str(said)
    text = " ".join(text.split())

    return text if len(text) <= SHOWN else text[:SHOWN] + ELLIPSIS
