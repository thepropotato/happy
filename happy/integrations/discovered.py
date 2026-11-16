"""The MCP servers already set up on this computer for Claude, Codex, Cursor, VS Code and Windsurf."""

import json
import logging
import os
import sys
import tomllib
from pathlib import Path, PureWindowsPath

HOME = Path.home()
log = logging.getLogger("happy.integrations")


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


def codex():
    """The user's Codex MCP servers, with environment values filled in for this run."""
    path = Path(os.environ["CODEX_HOME"]) / "config.toml" if os.environ.get("CODEX_HOME") else HOME / ".codex" / "config.toml"
    try:
        configured = tomllib.loads(path.read_text(encoding="utf-8")).get("mcp_servers") or {}
    except (OSError, UnicodeError, tomllib.TOMLDecodeError):
        log.debug("Could not read Codex MCP config: %s", path)
        return {}
    if not isinstance(configured, dict):
        return {}

    found = {}
    for name, entry in configured.items():
        if not isinstance(entry, dict) or entry.get("enabled") is False:
            continue
        if entry.get("url"):
            spec = {"url": entry["url"]}
            headers = dict(entry.get("http_headers") or {})
            for header, variable in (entry.get("env_http_headers") or {}).items():
                if isinstance(variable, str) and variable in os.environ:
                    headers[header] = os.environ[variable]
            variable = entry.get("bearer_token_env_var")
            if isinstance(variable, str) and variable in os.environ:
                headers["Authorization"] = f"Bearer {os.environ[variable]}"
            if headers:
                spec["headers"] = headers
        else:
            spec = {key: entry[key] for key in ("command", "args", "cwd") if key in entry}
            env = dict(entry.get("env") or {})
            env_vars = entry.get("env_vars") or []
            if isinstance(env_vars, (str, dict)):
                env_vars = [env_vars]
            for item in env_vars:
                variable = item if isinstance(item, str) else item.get("name") if isinstance(item, dict) else None
                if isinstance(variable, str) and variable in os.environ:
                    env[variable] = os.environ[variable]
            if env:
                spec["env"] = env
        if entry.get("auth") == "chatgpt":
            spec["codex_only"] = True
        found[name] = spec
    return found


SOURCES = {
    "Claude Code": claude_code,
    "Codex": codex,
    "Claude Desktop": lambda: read(support("Claude", "claude_desktop_config.json")).get("mcpServers") or {},
    "Cursor": lambda: read(HOME / ".cursor" / "mcp.json").get("mcpServers") or {},
    "VS Code": lambda: read(support("Code", "User", "mcp.json")).get("servers") or {},
    "Windsurf": lambda: read(HOME / ".codeium" / "windsurf" / "mcp_config.json").get("mcpServers") or {},
}


def usable(spec):
    if not isinstance(spec, dict) or spec.get("disabled") or spec.get("codex_only"):
        return False
    return bool(spec.get("command") or spec.get("url") or spec.get("serverUrl"))


def offline_first(command, args):
    """npx asks npm about the package on every start, slow behind a proxy; --prefer-offline uses the copy it has."""
    args = list(args or [])
    name = lambda part: PureWindowsPath(str(part)).stem.lower()
    if name(command) == "npx":
        at = 0
    elif name(command) == "cmd" and len(args) > 1 and str(args[0]).lower() == "/c" and name(args[1]) == "npx":
        at = 2
    else:
        return args
    if not {"--prefer-offline", "--offline", "--prefer-online"} & set(map(str, args)):
        args.insert(at, "--prefer-offline")
    return args


def normalised(spec):
    out = {k: spec[k] for k in ("command", "args", "env", "cwd", "headers", "codex_only") if k in spec}
    if out.get("command") and (args := offline_first(out["command"], out.get("args"))):
        out["args"] = args
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
            if (usable(spec) or isinstance(spec, dict) and spec.get("codex_only")) and name not in found:
                found[name] = (normalised(spec), source)
    return found
