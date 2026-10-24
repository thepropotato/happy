"""Things the person asks Happy to remember, kept in ~/.happy/memory.md."""

from typing import Annotated

from happy import paths
from happy.tools import tool

NOTES = paths.HOME / "memory.md"


@tool(label="Remembering")
def remember(fact: Annotated[str, "the fact, written as a short sentence about the person"]):
    """Remember something the person told you to remember, for every future conversation."""
    NOTES.parent.mkdir(parents=True, exist_ok=True)
    with NOTES.open("a") as notes:
        notes.write(f"- {fact.strip()}\n")
    return "Remembered."


@tool(label="Forgetting")
def forget(fact: Annotated[str, "words from the fact to forget"]):
    """Forget something you were asked to remember."""
    if not NOTES.exists():
        return "There was nothing to forget."
    lines = NOTES.read_text().splitlines()
    kept = [line for line in lines if fact.lower() not in line.lower()]
    NOTES.write_text("\n".join(kept) + ("\n" if kept else ""))
    return "Forgotten." if len(kept) < len(lines) else "I had nothing like that remembered."
