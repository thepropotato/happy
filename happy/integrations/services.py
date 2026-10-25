"""Bring your own MCP: whatever install command a service gives for Claude or Codex, registered once for every model."""

import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from happy.config import Config, save_secret, secrets

GMAIL_URL = "https://gmailmcp.googleapis.com/mcp/v1"
GMAIL_GUIDE = "https://developers.google.com/workspace/gmail/api/guides/configure-mcp-server"
NOISE = {"mcp", "www", "api", "app", "server", "servers", "com", "io", "dev", "ai", "net", "org", "co", "sh", "cloud", "v1", "sse"}
RUNNERS = {"npx", "uvx", "bunx", "pipx", "node", "python", "python3", "docker", "deno", "uv"}


def claude():
    """The claude command, which keeps the list of MCP servers that every model here reads."""
    found = shutil.which("claude") or str(Path.home() / ".local" / "bin" / "claude")
    return found if Path(found).exists() else None


def name_from_url(url):
    host = urlparse(url).netloc.split(":")[0]
    words = [w for w in re.split(r"[.\-]", host) if w and w not in NOISE]
    return (words[0] if words else "service").lower()


def name_from_package(tokens):
    for token in tokens[1:]:
        if not token.startswith("-"):
            bare = token.split("@")[-2] if token.startswith("@") and token.count("@") > 1 else token
            bare = bare.rsplit("/", 1)[-1].split("@")[0]
            bare = re.sub(r"(^mcp[-_]|[-_]?mcp([-_]server)?$|^server[-_])", "", bare)
            return bare.lower() or "service"
    return "service"


def scoped(rest):
    """Puts the server in the user scope, since Happy is not inside any one project."""
    cut = rest.index("--") if "--" in rest else len(rest)
    before, after = rest[:cut], rest[cut:]
    kept = []
    skip = False
    for token in before[1:]:
        if skip:
            skip = False
            continue
        if token in ("-s", "--scope"):
            skip = True
            continue
        if token.startswith("--scope="):
            continue
        kept.append(token)
    return [before[0], "-s", "user"] + kept + after


def from_codex(tokens):
    name, rest = tokens[3], tokens[4:]
    out, command, url = ["add", "-s", "user"], [], None
    i = 0
    while i < len(rest):
        if rest[i] == "--":
            command = rest[i + 1:]
            break
        if rest[i] in ("--env", "-e") and i + 1 < len(rest):
            out += ["-e", rest[i + 1]]
            i += 2
            continue
        if rest[i] == "--url" and i + 1 < len(rest):
            url = rest[i + 1]
            i += 2
            continue
        i += 1
    if url:
        return out + ["--transport", "http", name, url], name
    return out + [name, "--"] + command, name


def from_json(text):
    data = json.loads(text)
    data = data.get("mcpServers") or data.get("servers") or data
    if "command" in data or "url" in data or "serverUrl" in data:
        source = data.get("url") or data.get("serverUrl") or ""
        data = {name_from_url(source) if source else name_from_package([data.get("command", "")] + data.get("args", [])): data}
    name, spec = next(iter(data.items()))
    spec = dict(spec)
    if "serverUrl" in spec:
        spec["url"] = spec.pop("serverUrl")
    if "url" in spec and "type" not in spec:
        spec["type"] = "http"
    return ["add-json", "-s", "user", name, json.dumps(spec)], name


def plan(text):
    """The `claude mcp` arguments for what was pasted, and the server's name."""
    text = text.strip().strip("`").strip()
    if not text:
        raise ValueError("Paste the install command from the service's docs.")
    if text.startswith("{"):
        return from_json(text)
    if re.match(r"https?://", text):
        name = name_from_url(text)
        return ["add", "-s", "user", "--transport", "http", name, text], name
    tokens = shlex.split(text)
    if tokens[:2] == ["claude", "mcp"] and len(tokens) > 3 and tokens[2] in ("add", "add-json"):
        rest = scoped(tokens[2:])
        flags_with_values = {"-s", "--scope", "-t", "--transport", "-e", "--env", "-H", "--header", "--client-id", "--callback-port"}
        names = [t for i, t in enumerate(rest[1:], 1) if not t.startswith("-") and rest[i - 1] not in flags_with_values]
        return rest, names[0] if names else "service"
    if tokens[:3] == ["codex", "mcp", "add"] and len(tokens) > 3:
        return from_codex(tokens)
    if Path(tokens[0]).name in RUNNERS:
        name = name_from_package(tokens)
        return ["add", "-s", "user", name, "--"] + tokens, name
    raise ValueError("That doesn't look like an MCP install command. Paste the line the service gives for Claude Code or "
                     "Codex, its MCP URL, or its JSON config.")


def run(arguments, secret=None):
    cli = claude()
    if not cli:
        return False, "Claude Code is needed to keep the list of services; setup installs it."
    env = {**os.environ}
    if secret:
        env["MCP_CLIENT_SECRET"] = secret
    done = subprocess.run([cli, "mcp"] + arguments, capture_output=True, text=True, env=env, timeout=60,
                          stdin=subprocess.DEVNULL)
    message = (done.stdout + done.stderr).strip().splitlines()
    return done.returncode == 0, (message[-1] if message else "")


def add(text):
    """Registers a pasted service; returns (ok, message, name)."""
    try:
        arguments, name = plan(text)
    except (ValueError, json.JSONDecodeError) as error:
        return False, str(error), ""
    ok, message = run(arguments)
    return ok, (f"Added {name}." if ok else message or f"Could not add {name}."), name


def add_gmail(client_id, client_secret):
    """Google's official Gmail server, with the OAuth client Google requires each person to make."""
    from happy.integrations.oauth import PORT

    ok, message = run(["add", "-s", "user", "--transport", "http", "--client-id", client_id, "--client-secret",
                       "--callback-port", str(PORT), "gmail", GMAIL_URL], secret=client_secret)
    if ok:
        oauth = secrets().get("oauth", {})
        oauth["gmail"] = {"client_id": client_id, "client_secret": client_secret}
        save_secret("oauth", oauth)
    return ok, ("Added Gmail. Sign in to finish." if ok else message)


def remove(name):
    ok, message = run(["remove", name, "-s", "user"])
    return ok, (f"Removed {name}." if ok else message)


def removable():
    """Servers Happy itself can take away again: the ones in Claude Code's user list."""
    from happy.integrations.discovered import read, HOME

    return set((read(HOME / ".claude.json").get("mcpServers") or {}))


def sign_in_with_claude(name):
    """For Claude as the model: Claude Code keeps its own sign-ins, so its /mcp screen is opened, on screen."""
    from happy.tools.coding import open_terminal

    open_terminal(Path.home(), f"{shlex.quote(claude() or 'claude')} /mcp")
    return f"Opened Claude Code's MCP screen. Pick {name} there and sign in."


def connectors():
    """The claude.ai connectors on the person's account, as {name: connected}; they live there, in no file here."""
    if not claude():
        return {}
    try:
        listed = subprocess.run([claude(), "mcp", "list"], capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    found = {}
    for line in listed.splitlines():
        if line.startswith("claude.ai ") and ":" in line:
            found[line.split(":", 1)[0].removeprefix("claude.ai ").strip()] = "Connected" in line
    return found


def using_claude():
    return Config().get("brain.kind") in ("claude", "auto") and claude() is not None
