"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

from langchain_core.tools import tool
from typing import Literal

from hands import reasons
from hands.routines import picking
from hands.routines.picking import NONE, TAKEN
from memory import lifting, routines


def run_routine(name: str) -> str:
    """Run one of the person's saved routines by name. Use this the moment what they
    ask for matches what a saved routine does, whether or not they say the word
    routine — "run my morning brief", "do the standup thing", or just "morning brief".
    The routine does the whole job itself, with its own tools, and hands back the
    answer it ended on. Say that answer back to the person and do not go and do the
    job a second time yourself."""
    found, complaint = picking.only(name)

    if complaint:
        return complaint

    from brain import running

    routines.ran(found["name"])

    return running.run(found, picking.asked() or found["name"])


def save_routine(
    name: str,
    description: str,
    ends_with: str = "",
    steps: str = "",
    turns: int = 1,
    replace: bool = False,
) -> str:
    """Save what was just done as a routine, so it can be run again later on the word.
    Call this when the person says to save, keep or remember something as a routine,
    or asks you to always do it that way.

    Every word you write here describes the job they asked for, and never the answer
    that came back. What came back was true this once and will be different tomorrow,
    so a routine built out of it is one nobody can ask for again.

    Say they had just asked where they were and what was open, and got told they were
    in India with two windows up. Then: name is "where am I", description is "says
    where this computer is and what is open on it", and ends_with is "the place and how
    many windows are open". Not "India", not "two windows", and nothing at all about
    having saved anything — ends_with is what a good run of this finishes on next time,
    not what you are about to say to them now.

    Do not ask them what to call it. Give it a short name they would plausibly say out
    loud, two or three words, spaces between them and no punctuation at all, and tell
    them what you called it once it is saved.

    Leave steps empty unless the person spelt out something that did not actually
    happen: the steps and the tools are taken off the run that just worked, which is
    the whole reason a routine is worth anything.

    Leave turns alone. Where a job took several things said — what is unread, then
    more about one of them — the earlier turns are worked out and taken in on their
    own, by following what each tool was handed back to the tool that found it. Raise
    turns only when they have said to keep the last few things and none of it was
    joined up that way. Set replace only when they have said to overwrite an existing
    one.

    What comes back says which of their words it was actually taken from. Read it. If
    that is not the job you have just named, say so rather than letting it stand."""
    called = routines.tidy(name)

    if not called:
        return reasons.no("A routine needs a name to be saved under.")

    if routines.one(called) and not replace:
        return reasons.no(TAKEN.format(name=called))

    made = lifting.off(lifting.behind(turns))
    written, pointed = picking.grounded(steps.strip() or made["steps"])

    saved = routines.save(
        called,
        description=description,
        steps=written,
        tools=sorted(set(made["tools"]) | set(pointed)),
        examples=made["examples"],
        result=ends_with,
        asked=" ".join(made["asked"]),
    )

    if saved is None:
        return reasons.no("That routine would not save.")

    return f'Saved it as "{saved["name"]}". {picking.captured(saved)}'


def rename_routine(name: str, to: str) -> str:
    """Rename a saved routine. Everything it does stays exactly as it was and only what
    it is called changes. Use this whenever the person wants a different name for one —
    "call it something else", "rename that to the morning one"."""
    found, complaint = picking.only(name)

    if complaint:
        return complaint

    called = routines.tidy(to)

    if not called:
        return reasons.no("A routine needs a name to be renamed to.")

    if routines.one(called) and routines.plain(called) != routines.plain(found["name"]):
        return reasons.no(TAKEN.format(name=called))

    saved = routines.rename(found["name"], called)

    if saved is None:
        return reasons.no("That rename would not go through.")

    return f'That one is called "{saved["name"]}" now.'


def forget_routine(name: str) -> str:
    """Delete a saved routine for good. Only when the person has actually asked for it
    to go — "forget that routine", "get rid of the morning one". Renaming or changing
    one is not deleting it."""
    found, complaint = picking.only(name)

    if complaint:
        return complaint

    gone = routines.forget(found["name"])

    return f'Forgotten "{gone["name"]}".'


def my_routines(name: str = "") -> str:
    """What the person has saved as routines, and what each one actually does. Asked
    what routines they have, leave name empty and hear about all of them — never guess
    at a name to ask about. Give a name only when they asked about one in particular,
    and then you hear about that one and no other: how many steps it has, which tools
    it uses, how often they run it. This never runs anything."""
    if name:
        found, complaint = picking.only(name)

        return complaint or picking.described(found)

    kept = routines.every()

    return "\n".join(picking.described(each) for each in kept) if kept else NONE



ACTIONS = Literal["run", "save", "rename", "forget", "list"]


@tool
def routine(action: ACTIONS, name: str = "", description: str = "", ends_with: str = "",
            to: str = "", steps: str = "", turns: int = 1, replace: bool = False) -> str:
    """A saved routine: a job this person taught once and asks for again by name.
    Call "run" the moment a request matches what a saved routine does, before any
    other tool, and say back what it answers without redoing the job. Their saved
    routines are listed in the prompt.

    action: "run" with name, e.g. "morning brief". "save" with name, description
    (what the job does, never the answer that came back) and ends_with (what a
    good run finishes on); pick a two or three word name yourself. "rename" with
    name and to. "forget" with name, only when told to get rid of it. "list" with
    name empty for all, or a name for one. Leave steps and turns alone unless the
    person spelt them out; set replace only when told to overwrite."""
    if action == "run":
        return run_routine(name)

    if action == "save":
        return save_routine(name, description, ends_with, steps, turns, replace)

    if action == "rename":
        return rename_routine(name, to)

    if action == "forget":
        return forget_routine(name)

    return my_routines(name)


TOOLS = [routine]
