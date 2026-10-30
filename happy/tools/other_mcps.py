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
    """Search the extra MCP services set up on this computer for a tool that can do something. Asking Claude or Codex to do a job is hand_off_coding, not a service."""
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


def tool_name(server, name):
    return re.sub(r"[^A-Za-z0-9_-]", "_", f"{server}__{name}")[:64]


def short_schema(schema):
    """The server's input schema with its long descriptions cut, to keep a small model's prompt small."""
    schema = json.loads(json.dumps(schema or {"type": "object", "properties": {}}))
    for spec in (schema.get("properties") or {}).values():
        if isinstance(spec, dict) and len(spec.get("description", "")) > 100:
            spec["description"] = spec["description"][:100]
    schema.setdefault("required", [])
    return schema


def register_direct(most=40):
    """Hands connected servers' tools to local models as their own, while they fit; the rest stay behind the search."""
    from happy.tools import REGISTRY, Tool

    added = 0
    for server in hub.inherited():
        if server.client is None:
            continue
        for item in server.tools:
            if added >= most:
                return added
            name = tool_name(server.name, item.name)

            async def run(_server=server.name, _tool=item.name, **arguments):
                return await hub.call(_server, _tool, arguments)

            schema = short_schema(item.input_schema)
            REGISTRY[name] = Tool(name=name, fn=run, description=f"From the {server.name} service: {(item.description or item.name).strip()[:300]}",
                                  schema=schema, label=f"{server.name}: {item.name.replace('_', ' ')}",
                                  local_only=True, params=schema.get("properties") or {})
            added += 1
    return added
