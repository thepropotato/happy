"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

from langchain_core.tools import tool

from hands.owner import finding

NOBODY = (
    "Nothing signed in here has a name for them. Ask what to call them and use that, "
    "and never call them the user."
)


@tool
def who_i_work_for() -> str:
    """Say the name of the person whose computer this is — the one you belong to.

    Call this before their name has to appear anywhere: writing to somebody else
    on their behalf, saying whose assistant you are, or being asked what you know
    about them. It reads the name off what they have already signed in to, so it
    is the name they actually go by rather than a guess. Never invent it, and
    never fall back to calling them the user.
    """
    found, where = finding.named()

    return f"{found}, off {where}." if found else NOBODY


TOOLS = [who_i_work_for]
