"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

from langchain_core.tools import tool

from hands.owner import finding

NOBODY = (
    "Nothing signed in here has a name for them. Ask what to call them and use that, "
    "and never call them the user."
)

ALSO = " Elsewhere: {said}."


@tool
def who_i_work_for() -> str:
    """Say the name of the person whose computer this is — the one you belong to.

    Call this before their name has to appear anywhere: writing to somebody else
    on their behalf, telling somebody else whose assistant you are, or being asked
    what you know about them. Do not call it to answer them about you — asked who
    you are by the person whose computer this is, you are talking to them, and
    their name has no place in the answer. It asks every service they have
    connected — their mail, their
    chats, their accounts — and this computer as well, so what comes back is the
    name they actually go by rather than a guess. Where it also gives you what
    they are called somewhere else, that is the same person under a handle, not
    another person. Never invent the name, and never fall back to calling them
    the user.
    """
    found, where, others = finding.named()

    if not found:
        return NOBODY

    said = f"{found}, off {where}."

    if others:
        said += ALSO.format(said=", ".join(f"{name} on {place}" for name, place in others))

    return said


TOOLS = [who_i_work_for]
