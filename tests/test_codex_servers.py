"""Codex MCP servers are discovered read-only and can be removed with Codex itself."""

import json
from types import SimpleNamespace

import pytest

from happy.integrations import discovered, services


@pytest.fixture
def codex_config(tmp_path, monkeypatch):
    codex_home = tmp_path / "codex"
    codex_home.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setattr(discovered, "HOME", tmp_path)
    return codex_home / "config.toml"


def test_stdio_environment_and_cwd_are_mapped(codex_config, monkeypatch):
    codex_config.write_text('''
[mcp_servers.worker]
command = "node"
args = ["server.js"]
cwd = "/tmp/work"
env = { BASE = "local" }
env_vars = ["CODEX_TOKEN", "NOT_SET", { name = "OPTIONAL_TOKEN" }]
''')
    monkeypatch.setenv("CODEX_TOKEN", "secret-stdio")
    monkeypatch.setenv("OPTIONAL_TOKEN", "secret-optional")

    spec = discovered.codex()["worker"]
    assert spec == {"command": "node", "args": ["server.js"], "cwd": "/tmp/work",
                    "env": {"BASE": "local", "CODEX_TOKEN": "secret-stdio", "OPTIONAL_TOKEN": "secret-optional"}}
    assert discovered.usable(spec)


def test_url_headers_are_filled_from_environment(codex_config, monkeypatch):
    codex_config.write_text('''
[mcp_servers.remote]
url = "https://example.test/mcp"
http_headers = { "X-Static" = "visible" }
env_http_headers = { "X-Api-Key" = "API_KEY" }
bearer_token_env_var = "BEARER"
''')
    monkeypatch.setenv("API_KEY", "secret-header")
    monkeypatch.setenv("BEARER", "secret-bearer")

    assert discovered.codex()["remote"] == {
        "url": "https://example.test/mcp",
        "headers": {"X-Static": "visible", "X-Api-Key": "secret-header", "Authorization": "Bearer secret-bearer"},
    }
    monkeypatch.delenv("BEARER")
    monkeypatch.delenv("API_KEY")
    assert discovered.codex()["remote"]["headers"] == {"X-Static": "visible"}


def test_disabled_and_chatgpt_auth_servers(codex_config):
    codex_config.write_text('''
[mcp_servers.disabled]
command = "disabled"
enabled = false

[mcp_servers.chatgpt]
url = "https://example.test/chatgpt"
auth = "chatgpt"
''')

    found = discovered.codex()
    assert "disabled" not in found
    assert found["chatgpt"]["codex_only"] is True
    assert not discovered.usable(found["chatgpt"])
    assert discovered.everything()["chatgpt"] == (found["chatgpt"], "Codex")


@pytest.mark.parametrize("contents", [None, "[mcp_servers\nbad ="])
def test_missing_and_malformed_configs_return_empty_with_one_debug_log(tmp_path, monkeypatch, caplog, contents):
    caplog.set_level("DEBUG", logger="happy.integrations")
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    monkeypatch.setattr(discovered, "HOME", tmp_path)
    path = tmp_path / "config.toml"
    if contents is not None:
        path.write_text(contents)
    assert discovered.codex() == {}
    assert len([record for record in caplog.records if record.levelname == "DEBUG"]) == 1


def test_empty_config_is_valid_and_home_codex_directory_is_used(tmp_path, monkeypatch):
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(discovered, "HOME", tmp_path)
    config = tmp_path / ".codex" / "config.toml"
    config.parent.mkdir()
    config.write_text("")
    assert discovered.codex() == {}


def test_unreadable_config_returns_empty_with_one_debug_log(tmp_path, monkeypatch, caplog):
    caplog.set_level("DEBUG", logger="happy.integrations")
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    (tmp_path / "config.toml").mkdir()
    assert discovered.codex() == {}
    assert len([record for record in caplog.records if record.levelname == "DEBUG"]) == 1


def test_codex_home_is_used_and_claude_code_wins_name_collision(codex_config, tmp_path):
    codex_config.write_text('[mcp_servers.shared]\ncommand = "codex"\n')
    (tmp_path / ".claude.json").write_text(json.dumps({"mcpServers": {"shared": {"command": "claude"}}}))
    found = discovered.everything()
    assert found["shared"] == ({"command": "claude"}, "Claude Code")
    assert discovered.codex()["shared"]["command"] == "codex"


def test_settings_rows_and_services_json_never_contain_tokens(codex_config, monkeypatch, tmp_path):
    codex_config.write_text('''
[mcp_servers.remote]
url = "https://example.test/mcp"
bearer_token_env_var = "TOKEN"

[mcp_servers.inside]
url = "https://example.test/inside"
auth = "chatgpt"
''')
    monkeypatch.setenv("TOKEN", "never-persist-this")
    monkeypatch.setattr("happy.ui.settings.SERVICES_SEEN", tmp_path / "services.json")
    monkeypatch.setattr(services, "removable", lambda: set())
    monkeypatch.setattr(services, "connectors", lambda: {})
    added = []

    class Server:
        tools = []
        error = "not connected"

        async def connect(self, timeout=12):
            return False

    class Hub:
        def __init__(self):
            self.servers = {}

        def add(self, name, spec, source):
            added.append(name)
            self.servers[name] = Server()

        def get(self, name):
            return self.servers[name]

        async def close(self):
            pass

    monkeypatch.setattr("happy.integrations.mcp.Hub", Hub)
    from happy.ui.settings import Settings

    settings = Settings(lambda event: None)
    settings.check_services()
    rows = settings.services
    assert next((row for row in rows if row["name"] == "inside"), None) == {
        "name": "inside", "source": "Codex", "state": "only works inside Codex", "detail": "", "removable": False
    }, (rows, settings.notice)
    assert "inside" not in added
    assert "never-persist-this" not in json.dumps(rows)
    assert "never-persist-this" not in (tmp_path / "services.json").read_text()


def test_claude_options_include_http_headers(monkeypatch):
    from happy.agent import claude

    monkeypatch.setattr(claude, "create_sdk_mcp_server", lambda *args, **kwargs: "happy-server")
    monkeypatch.setattr(claude.tools, "available", lambda **kwargs: [])
    monkeypatch.setattr(claude, "ClaudeAgentOptions", lambda **kwargs: kwargs)
    monkeypatch.setattr(discovered, "claude_code", lambda: {})
    instance = claude.Claude.__new__(claude.Claude)
    instance.cfg = SimpleNamespace(get=lambda key: None)
    instance.model = "sonnet"
    instance.extra_servers = {"remote": {"url": "https://example.test/mcp", "headers": {"Authorization": "Bearer secret"}}}
    instance.resuming = None

    options = instance.options()
    assert options["mcp_servers"]["remote"] == {
        "type": "http", "url": "https://example.test/mcp", "headers": {"Authorization": "Bearer secret"}}


def test_removable_codex_requires_cli_and_removal_uses_source(codex_config, monkeypatch):
    codex_config.write_text('[mcp_servers.remote]\ncommand = "node"\n')
    monkeypatch.setattr(discovered, "claude_code", lambda: {"claude-server": {"command": "node"}})
    monkeypatch.setattr(services.shutil, "which", lambda command: None)
    assert "remote" not in services.removable()
    monkeypatch.setattr(services.shutil, "which", lambda command: "codex.exe" if command == "codex" else None)
    assert "remote" in services.removable()

    calls = []
    monkeypatch.setattr(services.subprocess, "run", lambda args, **kwargs: calls.append(args) or
                        SimpleNamespace(returncode=0, stdout="removed", stderr=""))
    assert services.remove("remote") == (True, "Removed remote.")
    assert calls[-1] == ["codex.exe", "mcp", "remove", "remote"]

    monkeypatch.setattr(discovered, "everything", lambda: {"claude-server": ({}, "Claude Code")})
    monkeypatch.setattr(services, "run", lambda args: calls.append(args) or (True, ""))
    assert services.remove("claude-server") == (True, "Removed claude-server.")
    assert calls[-1] == ["remove", "claude-server", "-s", "user"]


def test_codex_removal_failure_is_clear(codex_config, monkeypatch):
    codex_config.write_text('[mcp_servers.remote]\ncommand = "node"\n')
    monkeypatch.setattr(services.shutil, "which", lambda command: "codex")
    monkeypatch.setattr(services.subprocess, "run", lambda *args, **kwargs:
                        SimpleNamespace(returncode=1, stdout="", stderr="permission denied"))
    assert services.remove("remote") == (False, "permission denied")


def test_connections_tool_reports_codex_only_without_connecting(codex_config, monkeypatch):
    import asyncio

    from happy.integrations import status

    codex_config.write_text('[mcp_servers.inside]\nurl = "https://example.test/inside"\nauth = "chatgpt"\n')
    monkeypatch.setattr(status, "claude_servers", {})
    rows = asyncio.run(status.mcp_servers())
    assert rows == [("inside", "Codex", "only works inside Codex", "")]