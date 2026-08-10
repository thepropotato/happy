"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

from langchain_core.tools import tool

from memory import knowledge


@tool
def remember_this(text: str) -> str:
    """Save something worth remembering long-term — a stated preference,
    a fact about the person's life, or a durable detail they just told you.
    Decide on your own whether it qualifies and call this immediately;
    do not ask the person first. Save only what would still matter months
    from now. Skip passing, momentary details."""
    knowledge.remember_note(text)
    return "Remembered."


@tool
def recall_something(question: str) -> str:
    """Search long-term memory for anything relevant to the current
    question or topic, before assuming you don't know something about
    the person. Returns the most relevant remembered notes, or nothing
    if there's no good match."""
    found = knowledge.search_memory(question)
    return "\n".join(found) if found else "Nothing relevant found."


TOOLS = [remember_this, recall_something]
