"""The person's other MCP servers, reached by local models through a search instead of a giant tool list."""

import json
import math
import re
from collections import Counter
from typing import Annotated

from happy.integrations.mcp import hub
from happy.tools import report, tool


def any_inherited():
    return bool(hub.inherited())


def words(text):
    return re.findall(r"[a-z0-9]+", (text or "").lower().replace("_", " "))


async def catalogue():
    tools = []
    for server in hub.inherited():
        if server.client is None and not server.error:
            report(f"Starting {server.name}")
            await server.connect(timeout=20)
        for t in server.tools:
            tools.append((server.name, t))
    return tools


def compact(schema):
    props = (schema or {}).get("properties") or {}
    need = set((schema or {}).get("required") or [])
    parts = []
    for name, spec in list(props.items())[:12]:
        kind = spec.get("type", "any")
        note = (spec.get("description") or "")[:60]
        parts.append(f"{name}{'' if name in need else '?'}: {kind}{' — ' + note if note else ''}")
    return "; ".join(parts) or "no arguments"


@tool(label="Looking for a tool to {need}", local_only=True, needs=any_inherited)
async def find_service_tool(need: Annotated[str, "what you want to do, in a few words"]):
    """Search the extra services set up on this computer (from Claude, Cursor and others) for a tool that can do something."""
    tools = await catalogue()
    if not tools:
        names = ", ".join(f"{s.name} ({s.error})" for s in hub.inherited())
        return f"None of the extra services would start: {names}."
    docs = [(server, t, words(f"{server} {t.name} {t.description}")) for server, t in tools]
    df = Counter(w for _, _, d in docs for w in set(d))
    query = words(need)
    scored = []
    for server, t, d in docs:
        counts = Counter(d)
        value = sum(counts[w] * math.log(1 + len(docs) / df[w]) / (1 + len(d) / 40) for w in query if w in counts)
        scored.append((value, server, t))
    best = [x for x in sorted(scored, key=lambda x: -x[0]) if x[0] > 0][:5]
    if not best:
        return "No tool for that. Services available: " + ", ".join(sorted({s for s, _ in tools}))
    return "\n".join(f"{server}.{t.name}: {(t.description or '').strip()[:200]} | arguments: {compact(t.input_schema)}"
                     for _, server, t in best)


@tool(label="Using {name}", local_only=True, needs=any_inherited)
async def use_service_tool(
    name: Annotated[str, "the server.tool name from find_service_tool"],
    arguments: Annotated[dict, "the tool's arguments as a JSON object"] = None,
):
    """Run a tool found with find_service_tool."""
    server, _, tool_name = name.partition(".")
    if not tool_name:
        return "Use the full server.tool name from find_service_tool."
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except ValueError:
            return "arguments must be a JSON object."
    result = await hub.call(server, tool_name, arguments or {})
    return result
