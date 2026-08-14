"""EVERY TOOL, ASKED TO SAY WHY BEFORE IT IS ALLOWED TO DO ANYTHING."""

import copy

from pydantic import Field, create_model

WHY = "why"

# PAID FOR ONCE PER TOOL PER REQUEST, AND THERE ARE DOZENS.
TOLD = "What you are doing and why."


def widened(tools):
    """THE SAME TOOLS, EACH ASKING FOR ONE MORE THING."""
    return [wider(each) for each in tools]


def wider(tool):
    """A COPY THAT ALSO WANTS why, AND THROWS IT AWAY BEFORE THE TOOL RUNS."""
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


# A NO IS MARKED ON THE FRONT OF WHAT A TOOL SAYS AND TAKEN OFF AGAIN BEFORE THE MODEL EVER
# READS IT, THE SAME DEAL why GETS.
NOPE = "\ue000"


def no(said):
    """A TOOL'S ANSWER, MARKED AS A NO."""
    return f"{NOPE}{said}"


def went(said):
    """WHAT A TOOL SAID AND WHETHER IT WAS A NO, WITH THE MARK TAKEN BACK OFF."""
    if isinstance(said, str) and said.startswith(NOPE):
        return said[len(NOPE) :], True

    return said, False


def without(call):
    """THE CALL'S ARGUMENTS AND ITS REASON, PULLED APART."""
    args = dict(call.get("args") or {})
    why = args.pop(WHY, None)

    return args, (why or None)
