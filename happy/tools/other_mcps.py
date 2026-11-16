"""The person's other MCP servers, reached by local models through a search instead of a giant tool list."""

import asyncio
import json
import math
import os
import re
from collections import Counter
from typing import Annotated

from happy import paths
from happy.integrations.mcp import hub
from happy.tools import report, shown, tool


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


# CLAUDE'S OWN TOOLS ARE SHUT OFF, SO THE CONNECTOR IS ALL IT CAN TOUCH.
BUILT_IN = "Bash Edit Write Read Glob Grep WebFetch WebSearch NotebookEdit Task Agent Skill"


def account_connectors():
    """The claude.ai connectors the settings window last found, which reach any model through Claude Code."""
    try:
        rows = json.loads((paths.HOME / "services.json").read_text())
    except (OSError, ValueError):
        return []
    return [row["name"] for row in rows if row.get("source") == "claude.ai" and row.get("state") != "sign in on claude.ai"]


def through_claude():
    from happy.integrations import services

    return not services.using_claude() and services.claude() is not None and bool(account_connectors())


def result_text(content):
    if isinstance(content, list):
        return "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    return str(content or "")


@tool(say="Working on it.", label="Through Claude: {request}", local_only=True, needs=through_claude)
async def account_connector(
    service: Annotated[str, "the connector as named: Gmail, Google Drive and so on"],
    request: Annotated[str, "the whole job in plain words, with every name, address and wording they gave"],
):
    """Use a connector on the person's Claude account (Gmail, Google Drive and the like) to read, search, draft or send. Claude does the job with that connector alone, and every step it takes shows on screen."""
    from happy.agent import Act, Acted
    from happy.integrations import services

    names = account_connectors()
    name = next((n for n in names if n.lower() == service.lower()), None) or next((n for n in names if service.lower() in n.lower()), None)
    if not name:
        return f"No connector called {service}. The ones on the Claude account: {', '.join(names) or 'none'}."
    prefix = "mcp__claude_ai_" + re.sub(r"[^A-Za-z0-9]", "_", name)
    env = {k: v for k, v in os.environ.items() if k != "ELECTRON_RUN_AS_NODE"}
    done = await asyncio.create_subprocess_exec(
        services.claude(), "-p", request, "--output-format", "stream-json", "--verbose", "--no-session-persistence",
        "--allowedTools", prefix, "--disallowedTools", BUILT_IN,
        "--append-system-prompt", f"Use only the {name} tools. Do exactly what is asked and nothing more. Answer in a few plain sentences, without markdown.",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env, limit=16 * 1024 * 1024, cwd=str(paths.HOME))
    sink, open_calls, answer, failed = shown.get(), {}, "", False
    async for raw in done.stdout:
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        if event.get("type") == "result":
            answer, failed = event.get("result") or "", event.get("is_error") or event.get("subtype") != "success"
            continue
        for block in (event.get("message") or {}).get("content") or [] if event.get("type") in ("assistant", "user") else []:
            if not isinstance(block, dict):
                continue
            # ONLY THE CONNECTOR'S OWN CALLS ARE ACTIONS; CLAUDE LOOKING ITS TOOLS UP IS PLUMBING.
            if block.get("type") == "tool_use" and block.get("name", "").startswith(prefix + "__"):
                step = block["name"].removeprefix(prefix + "__")
                row = tool_name(name, step)
                open_calls[block.get("id")] = row
                report(f"{name}: {step.replace('_', ' ')}")
                if sink:
                    sink(Act(tool=row, args=block.get("input") or {}, label=f"{name}: {step.replace('_', ' ')}"))
            elif block.get("type") == "tool_result" and block.get("tool_use_id") in open_calls:
                row = open_calls.pop(block["tool_use_id"])
                if sink:
                    sink(Acted(tool=row, result=result_text(block.get("content"))[:2000], ok=not block.get("is_error")))
    await done.wait()
    if failed or not answer:
        problem = answer or (await done.stderr.read()).decode(errors="replace").strip()[-300:] or "Claude stopped without an answer."
        raise RuntimeError(problem)
    return answer
