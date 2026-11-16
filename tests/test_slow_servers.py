"""One slow MCP server neither hides the claude.ai connectors nor makes npx ask npm on every start."""

import asyncio
import subprocess
import time
import types

from happy.integrations import discovered, services
from happy.ui import settings


def test_npx_uses_the_copy_it_has():
    assert discovered.normalised({"command": "npx", "args": ["-y", "@acme/mcp"]})["args"] == ["--prefer-offline", "-y", "@acme/mcp"]
    assert discovered.normalised({"command": "C:\\nodejs\\npx.cmd", "args": ["@acme/mcp"]})["args"][0] == "--prefer-offline"
    assert discovered.normalised({"command": "cmd", "args": ["/c", "npx", "-y", "@acme/mcp"]})["args"] == \
        ["/c", "npx", "--prefer-offline", "-y", "@acme/mcp"]


def test_a_chosen_npm_mode_and_other_runners_are_left_alone():
    assert discovered.normalised({"command": "npx", "args": ["--prefer-online", "@acme/mcp"]})["args"] == ["--prefer-online", "@acme/mcp"]
    assert discovered.normalised({"command": "uvx", "args": ["acme-mcp"]})["args"] == ["acme-mcp"]
    assert "args" not in discovered.normalised({"url": "https://mcp.example.com"})


def test_a_list_that_times_out_is_unknown_not_empty(monkeypatch):
    monkeypatch.setattr(services, "claude", lambda: "claude")

    def slow(*args, **kwargs):
        raise subprocess.TimeoutExpired("claude", kwargs.get("timeout"))

    monkeypatch.setattr(subprocess, "run", slow)
    assert services.connectors() is None


class Server:
    def __init__(self, slow):
        self.slow, self.tools, self.error = slow, ["t"], None

    async def connect(self, timeout):
        await asyncio.sleep(timeout if self.slow else 0)
        return not self.slow


class Hub:
    def __init__(self):
        self.servers = {}

    def add(self, name, spec, source):
        self.servers[name] = Server(spec.get("slow"))

    def get(self, name):
        return self.servers[name]

    async def close(self):
        pass


def window(monkeypatch, listed, seen):
    from happy.integrations import mcp

    monkeypatch.setattr(mcp, "Hub", Hub)
    monkeypatch.setattr(discovered, "everything", lambda: {"quick": ({}, "Claude Code"), "slow": ({"slow": True}, "Cursor")})
    monkeypatch.setattr(services, "removable", lambda: set())
    monkeypatch.setattr(services, "connectors", listed)
    monkeypatch.setattr(settings, "SERVICE_CHECK", 5)
    monkeypatch.setattr(settings, "remembered_services", lambda: seen)
    monkeypatch.setattr(settings, "remember_services", lambda rows: None)
    one = settings.Settings.__new__(settings.Settings)
    one.services, one.notice, one.checking = None, "", True
    one.sent = []
    one.send = lambda: one.sent.append(list(one.services or []))
    return one


GMAIL = {"name": "Gmail", "source": "claude.ai", "state": "connected", "detail": "through Claude", "removable": False}


def test_servers_show_before_a_slow_connector_list(monkeypatch):
    def listed():
        time.sleep(2)
        return {"Gmail": True, "Google Drive": False}

    one = window(monkeypatch, listed, [GMAIL])
    one.check_services()
    early, final = one.sent[0], one.services
    assert [row["name"] for row in early] == ["Gmail", "quick", "slow"]
    assert {row["name"]: row["state"] for row in final} == \
        {"Gmail": "connected", "Google Drive": "sign in on claude.ai", "quick": "connected", "slow": "failing"}


def test_connectors_that_could_not_be_listed_stay_as_last_seen(monkeypatch):
    one = window(monkeypatch, lambda: None, [GMAIL, {"name": "old", "source": "Cursor"}])
    one.check_services()
    assert [row["name"] for row in one.services] == ["Gmail", "quick", "slow"]
