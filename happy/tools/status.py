"""Answering whether something is connected, from the connections themselves."""

from typing import Annotated

from happy.tools import tool

model_name = ""


@tool(label="Checking connections")
async def connections(about: Annotated[str, "the service asked about, like email or whatsapp; empty for all"] = ""):
    """Whether email, WhatsApp, the model and each MCP server are connected and working. Use this for any question about a connection or setup; it never needs an app opened."""
    from happy.integrations import status

    return await status.everything(model_name, about)
