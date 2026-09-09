"""A TOOL CALL THE BACKEND COULD NOT READ, AND WHAT THE MODEL IS SHOWN ABOUT IT.

LIFTED OUT OF brain/wrapping.py UNCHANGED. gpt-oss WRITES AN EXPRESSION WHERE A JSON VALUE
BELONGS — "x" * 100 — AND MORE OFTEN UNDER THE BIG PROMPT, SO THIS IS A RETRY RATHER THAN A
LOST TURN. TEMPERATURE IS USUALLY 0, SO AN UNCHANGED REQUEST WOULD COME BACK WORD FOR WORD
THE SAME: NAMING THE MISTAKE IS WHAT MAKES THE NEXT GO DIFFERENT, AND SHOWING THE MODEL ITS
OWN OUTPUT IS WORTH MORE THAN ANY RULE."""

import json
import uuid

from brain import mending

# HOW THE BACKEND SAYS THE MODEL WROTE SOMETHING IN A TOOL CALL THAT IS NOT JSON.
UNPARSED = ("error parsing tool call", "invalid tool call", "failed to parse tool")

# TEMPERATURE IS USUALLY 0, SO AN UNCHANGED REQUEST WOULD COME BACK WORD FOR WORD
# THE SAME. NAMING THE MISTAKE IS WHAT MAKES THE NEXT GO DIFFERENT.
AGAIN = (
    "Your last tool call could not be read: {trouble}. Tool arguments must be "
    "finished JSON values and never expressions — write the whole string out in "
    'full instead of anything like "hello" * 100 or "a" + "b". Make the call again.'
)

# THE SAME, FOR WHEN THE BACKEND QUOTED WHAT THE MODEL WROTE. SHOWING IT ITS OWN OUTPUT IS
# WORTH MORE THAN ANY RULE, AND THE ONE MISTAKE IT KEEPS MAKING IS WORTH NAMING OUTRIGHT.
SHOWN = (
    "Your last tool call could not be read: {trouble}\n\nYou wrote: {raw}\n\nThe arguments "
    "must be one flat JSON object: a single {{ at the start, a single }} at the end, and "
    "nothing but \"key\": value pairs in between. Never open a second {{ where a key should "
    "be. Write every value out in full and finish the object. Make the call again."
)



def minted():
    """AN ID FOR A CALL THE BACKEND NEVER GOT AS FAR AS GIVING ONE."""
    return f"mended_{uuid.uuid4().hex[:8]}"


def telling(said):
    """WHAT TO SAY BACK ABOUT AN UNREADABLE CALL: THE MISTAKE IT MADE, IN ITS OWN OUTPUT.

    TEMPERATURE IS 0, SO AN UNCHANGED REQUEST COMES BACK WORD FOR WORD THE SAME. SHOWING THE
    MODEL WHAT IT WROTE IS WHAT MAKES THE NEXT GO DIFFERENT."""
    raw = mending.wrote(said)

    return (SHOWN if raw else AGAIN).format(trouble=said, raw=raw)


def intended(said, tools):
    """THE ONE CALL AN UNREADABLE ONE CAN ONLY HAVE MEANT, AS (name, args), OR None.

    THE BACKEND SAYS WHAT THE MODEL WROTE BUT NOT WHICH TOOL IT WAS FOR, SO THE ARGUMENTS
    HAVE TO NAME IT: WHERE TWO TOOLS WOULD TAKE THEM THERE IS NO WAY TO CHOOSE, AND ASKING
    AGAIN BEATS CALLING THE WRONG ONE."""
    args = mending.mended(mending.wrote(said))

    if args is None:
        return None

    fits = [each.name for each in tools or [] if mending.fitting(args, wanted(each))]

    return (fits[0], args) if len(fits) == 1 else None


def wanted(tool):
    """A TOOL'S JSON SCHEMA, WHATEVER THE BINDING CALLS IT."""
    schema = getattr(tool, "args_schema", None)

    if schema is not None and hasattr(schema, "model_json_schema"):
        return schema.model_json_schema()

    return getattr(tool, "args", None) or {}


def unparsed(said):
    """WHETHER A FAILURE IS THE MODEL WRITING A BAD TOOL CALL, WHICH IS WORTH ANOTHER GO."""
    lowered = said.lower()

    return any(each in lowered for each in UNPARSED)



