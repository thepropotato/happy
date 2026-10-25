"""Setting, listing, moving, dropping and snoozing reminders by voice."""

from typing import Annotated, Literal

from happy import reminders, timing
from happy.tools import tool

When = Annotated[str, "the time in their own words, like 'at four', 'in ten minutes', 'tomorrow at nine', 'every weekday at 8'"]


def which(words):
    """The one reminder the words mean, or a sentence saying why not."""
    found = reminders.matching(words)
    if not found:
        return None, (f"No reminder about {words} is set." if words else "No reminders are set.")
    if len(found) > 1 and words:
        exact = [r for r in found if r["what"].lower() == words.lower()]
        if len(exact) != 1:
            return None, "More than one matches; which? " + "; ".join(reminders.described(r) for r in found[:5])
        found = exact
    return found[0], ""


@tool(label="Reminder: {action} {what}")
def reminder(
    action: Literal["set", "list", "change", "forget", "snooze"],
    what: Annotated[str, "set: the thing itself in few words ('call the dentist'); change, forget, snooze: words from the one meant"] = "",
    when: When = "",
    new_what: Annotated[str, "change: new words for it, only when they reword it"] = "",
    routine: Annotated[str, "set: the name of a saved routine to run at that time instead of only saying it"] = "",
):
    """Reminders. "set" with what and when ("every hour" and "every weekday at 8" repeat). "list" says what is coming up. "change" moves one to a new when or rewords it. "forget" drops one for good: "stop reminding me to drink water" and "cancel the dentist reminder" are forget. "snooze" puts off the one that just went off ("again in ten minutes"; when defaults to ten minutes)."""
    if action == "list":
        coming = reminders.upcoming()
        if not coming:
            return "No reminders are set."
        return "Coming up:\n" + "\n".join(reminders.described(r) for r in coming[:15])
    if action == "set":
        if not what.strip() and not routine:
            return "Say what the reminder is for."
        if routine:
            from happy import routines

            if not routines.named(routine):
                return f"There is no saved routine called {routine}."
        try:
            moment, rule = timing.when(when)
        except timing.Unclear as problem:
            return f"Not set: {problem}."
        made = reminders.add(what.strip() or f"run {routine}", moment, rule, routine)
        # THE TIME SAID BACK IN FULL IS THE WHOLE SAFETY NET, SO A WRONG GUESS IS HEARD AND CORRECTED.
        return f"Reminder set: {reminders.described(made)}."
    if action == "snooze":
        row = reminders.last_fired() if not what else which(what)[0]
        if not row:
            return "Nothing has gone off to snooze."
        try:
            moment, _ = timing.when(when or "in ten minutes")
        except timing.Unclear as problem:
            return f"Not snoozed: {problem}."
        if row["rule"]:
            made = reminders.add(row["what"], moment, None, row["routine"])
            return f"I'll remind you again at {timing.spoken(made['at'])}; the repeating one carries on as well."
        reminders.update(row["id"], due=moment, done=0)
        return f"I'll remind you again {timing.spoken(moment)}."
    row, problem = which(what)
    if not row:
        return problem
    if action == "forget":
        reminders.update(row["id"], done=1)
        return f"Forgot the reminder to {row['what']}."
    fields = {}
    if new_what.strip():
        fields["what"] = new_what.strip()
    if when.strip():
        try:
            moment, rule = timing.when(when)
        except timing.Unclear as problem:
            return f"Not changed: {problem}."
        if not rule and row["rule"] and "days" in row["rule"] and timing.clock(when.lower()):
            # "MAKE IT FIVE" FOR AN EVERY-DAY ONE MOVES THE HOUR IT REPEATS AT, NOT INTO A ONE-OFF.
            rule = {**row["rule"], "at": moment.strftime("%H:%M")}
            moment = timing.following(rule, timing.datetime.now())
        fields.update(due=moment, rule=rule)
    if not fields:
        return "Say the new time or the new words for it."
    changed = reminders.update(row["id"], **fields)
    return f"Changed: {reminders.described(changed)}."
