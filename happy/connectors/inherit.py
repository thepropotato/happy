"""The MCP servers already set up on this computer for Claude, Cursor, VS Code and Windsurf."""

import json
import os
import sys
from pathlib import Path

HOME = Path.home()


def support(*parts):
    if sys.platform == "darwin":
        return HOME / "Library" / "Application Support" / Path(*parts)
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", HOME)) / Path(*parts)
    return HOME / ".config" / Path(*parts)


def read(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def claude_code():
    data = read(HOME / ".claude.json")
    servers = dict(data.get("mcpServers") or {})
    servers.update((data.get("projects") or {}).get(str(HOME), {}).get("mcpServers") or {})
    return servers


SOURCES = {
    "Claude Code": claude_code,
    "Claude Desktop": lambda: read(support("Claude", "claude_desktop_config.json")).get("mcpServers") or {},
    "Cursor": lambda: read(HOME / ".cursor" / "mcp.json").get("mcpServers") or {},
    "VS Code": lambda: read(support("Code", "User", "mcp.json")).get("servers") or {},
    "Windsurf": lambda: read(HOME / ".codeium" / "windsurf" / "mcp_config.json").get("mcpServers") or {},
}


def usable(spec):
    if not isinstance(spec, dict) or spec.get("disabled"):
        return False
    return bool(spec.get("command") or spec.get("url") or spec.get("serverUrl"))


def normalised(spec):
    out = {k: spec[k] for k in ("command", "args", "env", "cwd") if k in spec}
    url = spec.get("url") or spec.get("serverUrl")
    if url:
        out["url"] = url
    return out


def everything():
    """Every server the person has set up elsewhere: {name: (spec, where it came from)}."""
    found = {}
    for source, reader in SOURCES.items():
        try:
            servers = reader()
        except Exception:
            continue
        for name, spec in servers.items():
            if usable(spec) and name not in found:
                found[name] = (normalised(spec), source)
    return found
