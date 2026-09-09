"""A SERVICE WITH TOO MANY TOOLS, BEHIND ONE DOOR UNTIL IT IS WANTED.

LINEAR HANDS OVER SEVENTY-THREE TOOLS. BOUND FLAT THEY MORE THAN DOUBLED THE TOOLSET, AND
EVERY ONE OF THEIR DESCRIPTIONS IS THEN READ BY THE MODEL ON EVERY TURN FOREVER — INCLUDING
THE TURNS ABOUT THE WEATHER. THE PREFIX CACHE IS THE WHOLE OF WHY HAPPY ANSWERS IN HALF A
SECOND, AND SEVENTY-THREE SCHEMAS SIT IN FRONT OF IT.

SO A BIG SERVICE GETS ONE TOOL IN THE STANDING PROMPT, SAYING WHAT IT IS FOR. THE MODEL CALLS
THAT WHEN IT WANTS THE SERVICE, AND WHAT COMES BACK IS THE REAL LIST — NAME, WHAT IT DOES AND
WHAT IT TAKES — WHICH IT THEN CALLS ON THE NEXT ROUND. ONE EXTRA ROUND, AND ONLY ON THE TURNS
THAT REACH FOR THAT SERVICE AT ALL.

A SMALL SERVICE IS NOT WORTH A DOOR: WEATHER'S FOUR TOOLS COST LESS TO SHOW THAN THE ROUND
TRIP WOULD, SO THEY STAY FLAT. THE LINE IS MANY, BELOW."""

import json

from langchain_core.tools import StructuredTool

from mcps import binding

# ABOVE THIS MANY TOOLS, A SERVICE GOES BEHIND A DOOR. GOOGLE'S SIXTEEN AND WHATSAPP'S
# FIFTEEN STAY IN FRONT: THEY ARE THE TWO ASKED FOR CONSTANTLY, AND A ROUND TRIP BEFORE
# EVERY "any unread messages" IS EXACTLY THE STALL HAPPY DOES NOT DO.
MANY = 20

# WHAT A DOOR SAYS. THE MODEL READS THIS AND NOTHING ELSE ABOUT THE SERVICE, SO IT CARRIES
# THE SERVICE'S NAME, WHAT IT IS FOR, AND WHAT PRESSING IT GETS YOU.
DOOR = (
    "{service}. {blurb} This service has {many} tools and they are not listed here. Call "
    "this first to see them, with a few words saying what you are trying to do, and it "
    "answers with the ones that fit and exactly how to call them. Then call the one you "
    "want. Use this whenever the errand is about {service}."
)

# HOW MANY OF A SERVICE'S TOOLS COME BACK AT ONCE. ENOUGH TO HOLD THE RIGHT ONE, FEW ENOUGH
# THAT THE ANSWER IS NOT THE WALL THIS EXISTS TO AVOID.
SHOWN = 12

NOTHING = "{service} has nothing matching that. Its tools are: {names}"


def wanted(offered):
    """WHETHER THIS SERVICE IS BIG ENOUGH TO GO BEHIND A DOOR."""
    return len(offered) > MANY


def door(service, session, offered, blurb=""):
    """THE ONE TOOL A BIG SERVICE SHOWS THE MODEL, IN PLACE OF ALL OF THEM."""
    name = binding.named(service, "tools")

    return StructuredTool(
        name=name,
        description=DOOR.format(service=service, blurb=blurb or "", many=len(offered)).replace("  ", " "),
        args_schema={
            "type": "object",
            "properties": {
                "doing": {
                    "type": "string",
                    "description": "What you are trying to do, in a few words.",
                }
            },
            "required": ["doing"],
        },
        func=looking(service, offered),
    )


def looking(service, offered):
    """WHAT THE DOOR DOES: THE TOOLS THAT FIT, WORDED SO THE NEXT ROUND CAN CALL ONE."""

    def look(doing=""):
        found = nearest(doing, offered)

        if not found:
            return NOTHING.format(service=service, names=", ".join(each.name for each in offered))

        return "\n\n".join(spelled(service, each) for each in found)

    return look


def nearest(doing, offered, most=SHOWN):
    """THE TOOLS WHOSE NAME OR DESCRIPTION SHARES MOST WITH WHAT WAS ASKED FOR.

    PLAIN WORD OVERLAP AND NOTHING CLEVERER: AN EMBEDDING HERE WOULD BE A MODEL CALL INSIDE
    A TOOL CALL, WHICH IS THE STALL THIS IS TRYING TO AVOID. A MISS COSTS THE MODEL ONE MORE
    GO AT THE DOOR WITH BETTER WORDS, WHICH IS CHEAP; THE WHOLE LIST IS THE FALLBACK."""
    said = {each for each in words(doing) if len(each) > 2}

    if not said:
        return offered[:most]

    scored = []

    for tool in offered:
        against = words(f"{tool.name} {tool.description or ''}")
        shared = len(said & against)

        if shared:
            scored.append((shared, tool))

    if not scored:
        return offered[:most]

    scored.sort(key=lambda pair: -pair[0])

    return [tool for _, tool in scored[:most]]


def words(said):
    return {each for each in "".join(
        letter if letter.isalnum() else " " for letter in str(said or "").lower()
    ).split()}


def spelled(service, tool):
    """ONE TOOL AS THE MODEL NEEDS IT: WHAT IT IS CALLED HERE, WHAT IT DOES, WHAT IT TAKES."""
    name = binding.named(service, tool.name)
    said = " ".join((tool.description or "").split())
    lines = [f"{name}: {said}" if said else name]
    takes = arguments(tool)

    if takes:
        lines.append(f"  takes: {takes}")

    return "\n".join(lines)


def arguments(tool):
    """A TOOL'S ARGUMENTS IN ONE LINE, REQUIRED ONES MARKED, SO A CALL CAN BE WRITTEN."""
    schema = tool.inputSchema or {}
    properties = schema.get("properties") or {}

    if not properties:
        return ""

    needed = set(schema.get("required") or [])
    said = []

    for name, about in properties.items():
        kind = (about or {}).get("type") or "value"
        said.append(f"{name} ({kind}){'' if name in needed else ', optional'}")

    return "; ".join(said)


# WHAT IS BEHIND EACH DOOR: {door tool name: [the real tool names it lets through]}. THE
# GRAPH IS BUILT WITH EVERY TOOL SO ANY OF THEM CAN RUN; THIS SAYS WHICH ONES THE MODEL IS
# SHOWN, AND keep_opened IN brain/wrapping.py IS WHAT DOES THE HIDING.
behind = {}


def shut(doors):
    """WHAT IS HIDDEN THIS TIME ROUND. REBUILT WHENEVER THE TOOLS ARE."""
    behind.clear()
    behind.update(doors)


def hidden():
    """EVERY TOOL NAME THAT IS BEHIND SOME DOOR."""
    return {name for names in behind.values() for name in names}


def opened(said):
    """THE TOOL NAMES A TURN HAS EARNED THE RIGHT TO SEE, OUT OF THE DOORS IT HAS CALLED."""
    through = set()

    for name, names in behind.items():
        if name in said:
            through.update(names)

    return through
