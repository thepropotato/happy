"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

from langchain_core.tools import tool
from typing import Literal

from memory import conversation, knowledge

# HOW MANY EARLIER EXCHANGES ARE WORTH READING BACK, AND HOW MUCH OF EACH.
FEW = 5

SHOWN = 160


def remember_this(text: str) -> str:
    """Save something worth remembering long-term — a stated preference,
    a fact about the person's life, or a durable detail they just told you.
    Decide on your own whether it qualifies and call this immediately;
    do not ask the person first. Save only what would still matter months
    from now. Skip passing, momentary details."""
    knowledge.remember_note(text)
    return "Remembered."


def recall_something(question: str) -> str:
    """Search long-term memory for anything relevant to the current
    question or topic, before assuming you don't know something about
    the person. Returns the most relevant remembered notes, or nothing
    if there's no good match."""
    found = knowledge.search_memory(question)
    return "\n".join(found) if found else "Nothing relevant found."


def recall_conversation(about: str) -> str:
    """Look back through earlier conversations with this person for something
    said or done before: what was done with a project last week, the name they
    gave a file, what you answered the last time this came up. Give it one or
    two words that would have been in it, like "untitled" or "PS5".

    The last few turns are already in front of you; this is for everything
    further back, including before you were last closed. Use it before saying
    you do not remember. It returns the matching exchanges newest first, each
    with when it happened, what they said and what you answered."""
    found = [each for each in conversation.search(about, limit=FEW + 1)
             if each.get("id") != conversation.here.get()][:FEW]

    if not found:
        return "Nothing earlier mentions that."

    return "\n".join(line(each) for each in found)


def line(entry):
    when = (entry.get("at") or "")[:16].replace("T", " at ")
    said = short(entry.get("message") or "nothing")
    answered = short(entry.get("reply") or "nothing")

    return f"{when}: they said {said!r}; you answered {answered!r}"


def short(said):
    said = " ".join(said.split())

    return said if len(said) <= SHOWN else said[:SHOWN].rstrip() + "..."



ACTIONS = Literal["save", "recall", "earlier"]


@tool
def remember(action: ACTIONS, text: str) -> str:
    """Long-term memory. "save" with text keeps a durable fact or preference the
    person stated directly ("prefers Safari"), never a passing detail or anything
    sensitive; call it before saying you will remember. "recall" with a question
    returns saved notes that match. "earlier" with a word or two ("untitled",
    "PS5") searches past conversations, including before you were last closed:
    use it before saying you do not remember."""
    if action == "save":
        return remember_this(text)

    if action == "recall":
        return recall_something(text)

    return recall_conversation(text)


TOOLS = [remember]
