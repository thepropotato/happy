"""Things Happy knows about the person from earlier conversations, kept in ~/.happy/memory.md."""

import re
from typing import Annotated

from happy import paths
from happy.tools import tool

NOTES = paths.HOME / "memory.md"


def note(fact):
    """Adds a line to the notes unless it is already there, and says which happened."""
    fact = " ".join(fact.split()).rstrip(".") + "."
    NOTES.parent.mkdir(parents=True, exist_ok=True)
    lines = NOTES.read_text().splitlines() if NOTES.exists() else []
    if f"- {fact}".lower() in (line.lower() for line in lines):
        return "Already remembered."
    with NOTES.open("a") as notes:
        notes.write(f"- {fact}\n")
    return "Remembered."


@tool(label="Remembering")
def remember(fact: Annotated[str, "the fact as a short sentence, like 'My brother is John Doe in my contacts'"]):
    """Remember a fact for every future conversation. Call it when they ask you to remember something, and also without being asked whenever they explain who or what they mean: a person ('my brother is John Doe'), a place ('home is Flat 12, Example Residency') or an account. Then carry on with what they asked."""
    return note(fact)


@tool(label="Forgetting")
def forget(fact: Annotated[str, "words from the fact to forget"]):
    """Forget something you were asked to remember."""
    if not NOTES.exists():
        return "There was nothing to forget."
    lines = NOTES.read_text().splitlines()
    kept = [line for line in lines if fact.lower() not in line.lower()]
    NOTES.write_text("\n".join(kept) + ("\n" if kept else ""))
    return "Forgotten." if len(kept) < len(lines) else "I had nothing like that remembered."


@tool(label="Changing how I talk")
def personality(style: Annotated[str, "how to talk from now on, in their words, like 'like a knight from Game of Thrones'; empty to go back to normal"] = ""):
    """Change the way you talk from the next reply on, when they ask you to talk like someone or in some style, or to talk normally again."""
    from happy import persona

    style = style.strip()
    # A MODEL ASKED TO GO BACK TO NORMAL WRITES "normal" AS OFTEN AS IT LEAVES THE STYLE EMPTY.
    if re.fullmatch(r"(?:talk |speak )?(?:like )?(?:normal|normally|default|usual|your(?:self| own way| usual way| normal way)?|plain|regular|none|off|reset)\.?", style.lower()):
        style = ""
    persona.adopt(f"Talk {style}." if style and not style.lower().startswith(("talk", "speak")) else style)
    return "From the next reply on, I'll talk that way." if style else "Back to my own way of talking from the next reply."
