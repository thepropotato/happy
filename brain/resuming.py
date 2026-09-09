"""THE CONVERSATION BEFORE THIS SESSION, READ BACK OFF THE TABLE SO THE FIRST TURN IS NOT THE FIRST TURN."""

from datetime import datetime

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from brain.history import BRIEF, ELLIPSIS
from memory import conversation, settings

ID = "resumed-{row}-{number}"

# WHAT A TOOL RESULT FROM AN EARLIER SITTING IS LABELLED WITH. WITHOUT THIS A CHECK OF
# WHATSAPP AT TEN AND A CHECK AT THREE ARE THE SAME BYTES IN THE SAME SHAPE, AND ASKED THE
# SAME QUESTION AGAIN THE MODEL READ THE MORNING'S ANSWER AS ONE IT HAD JUST FETCHED AND SAID
# IT BACK WITHOUT CALLING ANYTHING. WHAT A TOOL SAID THEN IS NOT WHAT IT WOULD SAY NOW.
STALE = "[From an earlier turn, {ago}. This is what was true then, not now. Anything asked again must be looked up again.]\n"


def ago(row):
    """HOW LONG AGO THIS EXCHANGE WAS, IN THE ROUGH WORDS A PERSON WOULD USE."""
    stamp = row.get("epoch")

    if not stamp:
        return "earlier"

    seconds = max(0, datetime.now().astimezone().timestamp() - float(stamp))
    minutes = int(seconds // 60)

    if minutes < 2:
        return "just now"

    if minutes < 60:
        return f"{minutes} minutes ago"

    hours = minutes // 60

    if hours < 24:
        return f"{hours} hours ago" if hours > 1 else "an hour ago"

    days = hours // 24

    return f"{days} days ago" if days > 1 else "yesterday"


def messages(turns=None):
    """THE LAST FEW EXCHANGES AS THE MODEL WOULD HAVE SEEN THEM, OLDEST FIRST."""
    rows = conversation.history(turns or settings.get("brain.history"))
    rebuilt = []

    for row in rows:
        rebuilt += exchange(row)

    return rebuilt


def exchange(row):
    """ONE ROW AS THE MESSAGES IT WAS: WHAT WAS SAID, EACH CALL AND ITS SHORT ANSWER, THE REPLY."""
    said = row.get("message")
    reply = row.get("reply")

    if not said and not reply:
        return []

    when = STALE.format(ago=ago(row))

    out = [HumanMessage(said)] if said else []

    for number, call in enumerate(row.get("tools") or []):
        ident = ID.format(row=row.get("id"), number=number)
        args = dict(call.get("args") or {})

        if call.get("why"):
            args["why"] = call["why"]

        out.append(AIMessage(
            content="",
            tool_calls=[{"name": call.get("name"), "args": args, "id": ident, "type": "tool_call"}],
        ))
        out.append(ToolMessage(
            # THE AGE GOES ON THE RESULT ITSELF, NOT IN A NOTE BESIDE IT: THIS IS THE ONE
            # THING THE MODEL READS WHEN IT IS DECIDING WHETHER IT ALREADY KNOWS.
            content=when + brief(call.get("result")),
            tool_call_id=ident,
            name=call.get("name"),
            status="error" if call.get("failed") else "success",
        ))

    if reply:
        out.append(AIMessage(reply))

    return out


def brief(result):
    said = str(result or "")

    return said if len(said) <= BRIEF else said[:BRIEF].rstrip() + ELLIPSIS
