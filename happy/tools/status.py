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


@tool(label="Checking the {part}")
def clock(part: Literal["time", "date", "day", "all"] = "all"):
    """The current time, day or date here. Ask for only the part they asked about; "all" when counting days or they want everything."""
    shapes = {"time": "It's %I:%M %p.", "date": "It's %d %B %Y.", "day": "It's %A, %d %B.", "all": "It's %I:%M %p on %A, %d %B %Y."}
    return time.strftime(shapes.get(part, shapes["all"])).replace(" 0", " ")
