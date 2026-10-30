"""The real state of every connection: internet, model, WhatsApp and each MCP server, checked rather than assumed."""

import asyncio

import httpx

from happy.integrations import discovered, whatsapp
from happy.integrations.mcp import hub

claude_servers = {}


def whatsapp_state():
    if not whatsapp.installed():
        return "not installed", "Setup installs it"
    if not whatsapp.listening():
        return "not running", "its bridge is not up"
    state = whatsapp.status() or {}
    if not state.get("linked"):
        return "not linked", "scan the QR code in Settings > WhatsApp"
    who = state.get("name") or state.get("phone") or "your phone"
    if not state.get("connected"):
        return "linked but not connected", f"linked as {who}; reconnecting, so new messages are not coming in yet"
    return "connected", f"linked as {who}"


async def mcp_servers(only=None):
    """Each MCP server from other apps (or just the named ones), started if need be to see whether it really answers."""
    found = {name: spec for name, spec in discovered.everything().items() if not only or name in only}
    rows = []

    async def check(name, source):
        if name in claude_servers:
            return name, source, claude_servers[name], ""
        server = hub.get(name)
        if server is None:
            return name, source, "not loaded", ""
        if server.client is None:
            await server.connect(timeout=15)
        if server.client is not None:
            return name, source, "connected", f"{len(server.tools)} tools"
        error = server.error or "did not start"
        needs_sign_in = any(word in error.lower() for word in ("401", "unauthor", "auth"))
        return name, source, "needs sign-in" if needs_sign_in else "failing", error[:80]

    results = await asyncio.gather(*(check(name, source) for name, (_, source) in found.items()))
    for name, source, state, detail in results:
        rows.append((name, source, state, detail))
    for name, state in claude_servers.items():
        if name not in found and name not in ("happy", "whatsapp") and (not only or name in only):
            rows.append((name, "claude.ai" if name.startswith("claude.ai") else "Claude", state, ""))
    return rows


def internet():
    try:
        httpx.head("https://www.google.com/generate_204", timeout=4)
        return "online"
    except httpx.HTTPError:
        return "offline"


def concerns(about, *words):
    return not about or any(word in about for word in words)


async def everything(model_name="", about=""):
    """Lines of plain text, one per connection; with about, only the ones it concerns."""
    about = (about or "").lower()
    servers = set(discovered.everything()) | set(claude_servers)
    named = [name for name in servers if name.lower().replace("claude.ai ", "") in about]
    lines = []
    if concerns(about, "internet", "wifi", "wi-fi", "online", "network"):
        lines.append(f"Internet: {await asyncio.to_thread(internet)}")
    if concerns(about, "model", "claude", "brain", "ollama", "gpt"):
        lines.append(f"Model: {model_name or 'none chosen'}")
    if concerns(about, "whatsapp"):
        state, detail = await asyncio.to_thread(whatsapp_state)
        lines.append(f"WhatsApp: {state} ({detail})")
    if concerns(about, "mail", "gmail", "outlook", "inbox"):
        mailers = [name for name in servers if any(word in name.lower() for word in ("mail", "outlook", "inbox"))]
        if not mailers:
            # A CLAUDE.AI CONNECTOR LIVES ON THE ACCOUNT, NOT IN ANY FILE HERE, AND ONLY CLAUDE CODE CAN REACH IT.
            from happy.integrations import services

            account = [name for name in await asyncio.to_thread(services.connectors) if "mail" in name.lower()]
            if account:
                how = "" if services.using_claude() else "; account_connector reads, searches, drafts and sends it"
                lines.append(f"Email: {', '.join(account)} is connected on the Claude account{how}")
            else:
                lines.append("Email: no email service added (add Gmail or another email MCP server in Settings > Services)")
        for name, source, state, detail in await mcp_servers(mailers) if mailers else []:
            lines.append(f"Email through {name} (from {source}): {state}{f' ({detail})' if detail else ''}")
    if concerns(about, "mcp", "server", "connector", "service", "everything", "anything") or named:
        for name, source, state, detail in await mcp_servers(named or None):
            lines.append(f"MCP server {name} (from {source}): {state}{f' ({detail})' if detail else ''}")
    if not lines:
        return await everything(model_name)
    return "\n".join(lines)
