"""HOW ONE ROUTINE READS TO THE MODEL THAT IS ABOUT TO RUN IT."""

import json

# WHAT IS SAID ABOUT ${TOOL: x}, WHICH IS THE ONE THING TYING A LINE OF PROSE TO A REAL CALL.
POINTS = "${TOOL: name} says which tool a step is done with. Call that one, not one like it."

# WITHOUT THIS A SMALL MODEL READS THE EXAMPLE'S ANSWER AS TODAY'S ANSWER AND NEVER LOOKS,
# AND SENDS LAST WEEK'S MESSAGE ID BACK TO THE SERVICE THAT ISSUED IT.
SHAPE = (
    "How it went the last time this worked. Copy the shape of these calls and nothing that "
    "is in them. Both what went in and what came back were true that once: an id, a name, a "
    "date or an address in here is last time's and never this time's, so go and get today's "
    "the way that run got its own."
)

# THEIR OWN WORDS THE TIME IT WORKED, WHICH SAY WHAT THE JOB IS WHEREVER A DESCRIPTION
# WRITTEN AFTERWARDS HAS DRIFTED OFF IT.
SAID = 'What they said, the time this worked: "{asked}"'

OPENING = (
    'Everything below is one routine, called "{name}". It is the only thing you are doing '
    "this turn. Work through the steps in order, then answer."
)

def written(found):
    """THE ROUTINE AS THE MODEL READS IT."""
    parts = [OPENING.format(name=found["name"])]

    if found.get("description"):
        parts.append(f"What it does. {found['description']}")

    if found.get("steps"):
        parts.append("The steps.\n" + found["steps"])
        parts.append(POINTS)

    if found.get("examples"):
        parts.append(SHAPE + "\n" + "\n".join(showing(each) for each in found["examples"]))

    if found.get("asked"):
        parts.append(SAID.format(asked=found["asked"]))

    if found.get("result"):
        parts.append(f"What to end with. {found['result']}")

    return "\n\n".join(parts)

def showing(example):
    """ONE RECORDED CALL AS A LINE: WHAT WENT IN, AND WHAT CAME BACK THAT TIME."""
    args = json.dumps(example.get("args") or {}, default=str)
    result = example.get("result") or ""

    return f"- {example.get('name')} with {args} came back: {result}"
