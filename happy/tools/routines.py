"""Saving, running, listing, renaming and forgetting routines by voice."""

from typing import Annotated, Literal

from happy import history, routines
from happy.tools import tool


@tool(label="Routine: {action} {name}")
def routine(
    action: Literal["save", "run", "list", "rename", "forget"],
    name: Annotated[str, "the routine's name, like 'morning brief'"] = "",
    steps: Annotated[list[str], "save: each request in their words, like ['what's the weather', 'any unread WhatsApp messages']; empty to save the request just made"] = None,
    new_name: Annotated[str, "rename: what to call it now"] = "",
):
    """Routines: a named set of requests run together on the word. "save" keeps steps under a name (saving again replaces it); for "save that as a routine" leave steps empty and the request just made is kept. "run" does one: call it whenever a request matches a saved routine. "list" says what each does. "rename" and "forget" change or drop one."""
    if action == "list":
        found = routines.every()
        if not found:
            return "No routines are saved."
        return "\n".join(f"{r['name']}: " + "; ".join(r["steps"]) for r in found)
    if not name.strip():
        return "Say which routine."
    if action == "save":
        if not steps:
            earlier = [t["request"] for t in history.recent(limit=5) if t["request"] and t["how"] not in ("reminder", "routine")]
            # THE NEWEST TURN IS THIS VERY REQUEST TO SAVE, SO THE ONE BEFORE IT IS WHAT WAS DONE.
            steps = earlier[1:2]
        if not steps:
            return "Say what the routine should do."
        saved = routines.save(name, [s.strip() for s in steps if s.strip()])
        return f"Saved the {saved['name']} routine: " + "; ".join(saved["steps"]) + ". Say its name to run it."
    found = routines.named(name)
    if not found:
        known = ", ".join(r["name"] for r in routines.every())
        return f"There is no routine called {name}." + (f" The saved ones are: {known}." if known else "")
    if action == "run":
        return routines.request(found).removeprefix(f"Run my {found['name']} routine. ")
    if action == "rename":
        if not new_name.strip():
            return "Say the new name."
        routines.rename(name, new_name)
        return f"Renamed {found['name']} to {new_name.strip().lower()}."
    routines.forget(name)
    return f"Forgot the {found['name']} routine."
