"""THE CONVERSATION BEFORE THIS SESSION, READ BACK OFF THE TABLE SO THE FIRST TURN IS NOT THE FIRST TURN."""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from brain.history import BRIEF, ELLIPSIS
from memory import conversation, settings

ID = "resumed-{row}-{number}"


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
            content=brief(call.get("result")),
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
