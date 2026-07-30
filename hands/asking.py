"""EVERY TOOL, ASKED TO SAY WHY BEFORE IT IS ALLOWED TO DO ANYTHING.

THE REASON A TOOL RAN IS WORTH KEEPING, AND THE ONLY PLACE IT RELIABLY EXISTS IS
IN THE MODEL'S HEAD AT THE MOMENT IT DECIDES. ASKING AFTERWARDS COSTS A WHOLE
ROUND TRIP, WHICH IS ANOTHER SECOND OF SILENCE. TAKING WHATEVER THE MODEL HAPPENED
TO SAY OUT LOUD FIRST GETS NOTHING AT ALL WHEN IT WENT STRAIGHT FOR THE TOOL.

SO IT IS AN ARGUMENT LIKE ANY OTHER, REQUIRED BY THE SCHEMA, AND TAKEN BACK OUT
BEFORE THE TOOL ITSELF EVER SEES IT — NO TOOL HAS TO KNOW THIS HAPPENS.
"""

import copy

from pydantic import Field, create_model

WHY = "why"

# PAID FOR ONCE PER TOOL ON EVERY REQUEST, AND THERE ARE DOZENS, SO THE SHAPE OF
# THE SENTENCE IS SET ONCE IN THE STANDING PROMPT AND THIS ONLY NAMES THE FIELD.
TOLD = "What you are doing and why."


def widened(tools):
    """THE SAME TOOLS, EACH ASKING FOR ONE MORE THING."""
    return [wider(each) for each in tools]


def wider(tool):
    """A COPY THAT ALSO WANTS why, AND THROWS IT AWAY BEFORE THE TOOL RUNS.

    BOTH HALVES BELONG TOGETHER. WIDENING THE SCHEMA WITHOUT DEAFENING THE FUNCTION
    MEANS THE TOOL IS HANDED AN ARGUMENT IT NEVER DECLARED; TAKING why OFF THE CALL
    SOMEWHERE ELSE MEANS THIS SCHEMA THEN FAILS ON THE FIELD IT ASKED FOR.

    A COPY AND NOT A CHANGE, BECAUSE THE MODULES HAND BACK THE SAME TOOL OBJECT
    EVERY TIME THEY ARE ASKED AND THE GRAPH IS REBUILT WHENEVER A SETTING MOVES.
    """
    if WHY in (tool.args or {}):
        return tool

    schema = tool.args_schema

    try:
        asked = spread(schema) if isinstance(schema, dict) else grown(schema)
    except Exception:
        return tool

    changed = {"args_schema": asked}

    if getattr(tool, "func", None) is not None:
        changed["func"] = deaf(tool.func)

    if getattr(tool, "coroutine", None) is not None:
        changed["coroutine"] = deafly(tool.coroutine)

    return tool.model_copy(update=changed)


def deaf(call):
    """THE SAME FUNCTION, WHICH CANNOT HEAR why."""

    def ran(*args, **named):
        named.pop(WHY, None)

        return call(*args, **named)

    return ran


def deafly(call):
    """THE SAME, FOR A TOOL THAT IS AWAITED."""

    async def ran(*args, **named):
        named.pop(WHY, None)

        return await call(*args, **named)

    return ran


def grown(schema):
    """A PYDANTIC SCHEMA WITH why ADDED. WHAT A @tool IN THIS REPO HAS."""
    return create_model(
        f"{schema.__name__}_{WHY}",
        __base__=schema,
        **{WHY: (str, Field(..., description=TOLD))},
    )


def spread(schema):
    """A JSON SCHEMA WITH why ADDED. WHAT AN MCP SERVER HANDS OVER."""
    asked = copy.deepcopy(schema)

    asked.setdefault("properties", {})[WHY] = {"type": "string", "description": TOLD}
    asked["required"] = [*asked.get("required", []), WHY]

    return asked


def without(call):
    """THE CALL'S ARGUMENTS AND ITS REASON, PULLED APART.

    A COPY OF THE ARGUMENTS, BECAUSE THE ONES ON THE CALL BELONG TO THE MESSAGE
    THE MODEL SENT AND THE CONVERSATION KEEPS READING IT AFTERWARDS.
    """
    args = dict(call.get("args") or {})
    why = args.pop(WHY, None)

    return args, (why or None)
