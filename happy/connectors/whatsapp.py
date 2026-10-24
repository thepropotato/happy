"""The WhatsApp MCP server from its own folder, with the bridge that holds the linked phone running beside it."""

import atexit
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from happy import paths

PORT = int(os.environ.get("WHATSAPP_BRIDGE_PORT") or 3001)
ENV = paths.HOME / "envs" / "whatsapp"
bridge = None


def root(cfg):
    """The whatsapp-mcp folder: from the config, or sitting next to Happy's own folder."""
    named = cfg.get("whatsapp.path") or ""
    for folder in [Path(named).expanduser()] if named else [paths.REPO.parent / "whatsapp-mcp", Path.home() / "whatsapp-mcp"]:
        if (folder / "mcps" / "servers" / "whatsapp" / "mcp_server.py").exists():
            return folder
    return None


def python():
    exe = ENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    return str(exe) if exe.exists() else None


def listening():
    with socket.socket() as probe:
        probe.settimeout(0.3)
        return probe.connect_ex(("127.0.0.1", PORT)) == 0


def start_bridge(folder):
    """Starts the bridge unless one is already answering on its port."""
    global bridge
    folder = Path(folder)
    if listening():
        return True
    log = open(paths.HOME / "whatsapp-bridge.log", "a")
    bridge = subprocess.Popen([python(), str(folder / "mcps" / "servers" / "whatsapp" / "bridge.py")],
                              cwd=str(folder), stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    atexit.register(stop_bridge)
    for _ in range(60):
        if listening():
            return True
        if bridge.poll() is not None:
            return False
        time.sleep(0.5)
    return listening()


def stop_bridge():
    if bridge and bridge.poll() is None:
        bridge.terminate()
        try:
            bridge.wait(5)
        except subprocess.TimeoutExpired:
            bridge.kill()


def spec(cfg):
    """How to launch the WhatsApp MCP server, or None when it is not on this computer."""
    folder = root(cfg)
    if not folder or not python():
        return None
    return {"command": python(), "args": [str(folder / "mcps" / "servers" / "whatsapp" / "mcp_server.py")],
            "cwd": str(folder), "folder": str(folder)}
