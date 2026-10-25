"""Answering whether something is connected, from the connections themselves."""

import time
from typing import Annotated, Literal

from happy.tools import tool

model_name = ""


@tool(label="Checking connections")
async def connections(about: Annotated[str, "the service asked about, like email or whatsapp; empty for all"] = ""):
    """Whether email, WhatsApp, the model and each MCP server are connected and working. Use this for any question about a connection or setup; it never needs an app opened."""
    from happy.integrations import status

    return await status.everything(model_name, about)


# DAYS PEOPLE COUNT TO BY NAME, AS (MONTH, DAY).
NAMED_DAYS = {"christmas": (12, 25), "christmas eve": (12, 24), "new year": (1, 1), "new years": (1, 1),
              "new year's": (1, 1), "new year's eve": (12, 31), "valentine's day": (2, 14), "valentines day": (2, 14),
              "halloween": (10, 31), "independence day": (8, 15), "republic day": (1, 26)}


def countable(said, today=None):
    """The date a day's name or a spoken date means, or None when the words name no date."""
    from datetime import date, datetime

    from happy import timing

    today = today or date.today()
    plain = said.lower().strip().removeprefix("the ")
    if plain in NAMED_DAYS:
        month, day = NAMED_DAYS[plain]
        target = date(today.year, month, day)
        return target if target >= today else date(today.year + 1, month, day)
    try:
        return timing.day_named(plain, datetime.combine(today, datetime.min.time()))
    except timing.Unclear:
        return None


def days_until(said, today=None):
    """'Christmas is in 61 days, on Friday 25 December.' Counted in code, since a model counting days gets it wrong."""
    from datetime import date

    today = today or date.today()
    target = countable(said, today)
    if target is None:
        return f"I can't tell which date {said} is; say it as a date, like 25 December."
    named = said.lower().strip().removeprefix("the ") in NAMED_DAYS
    on = f"{target.strftime('%A')} {target.day} {target.strftime('%B')}" + (f" {target.year}" if target.year != today.year else "")
    count = (target - today).days
    if count == 0:
        return f"{said.strip().title() if named else 'That'} is today."
    days = f"{count} day{'s' if count != 1 else ''}"
    return f"{said.strip().title()} is in {days}, on {on}." if named else f"{on} is in {days}."


@tool(label="Checking the {part}{until}")
def clock(part: Literal["time", "date", "day", "all"] = "all",
          until: Annotated[str, "a day to count to, like 'christmas' or '21 May', for how many days until it"] = ""):
    """The current time, day or date here, or how many days until a date. Call it for every question about the time or date, including whether it is past an hour and how many days until a day, rather than working it out yourself. Ask for only the part they asked about."""
    if until.strip():
        return days_until(until)
    shapes = {"time": "It's %I:%M %p.", "date": "It's %d %B %Y.", "day": "It's %A, %d %B.", "all": "It's %I:%M %p on %A, %d %B %Y."}
    return time.strftime(shapes.get(part, shapes["all"])).replace(" 0", " ")
