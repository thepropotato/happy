"""WhatsApp, shipped with Happy: the bridge that holds the linked phone, and the MCP server beside it."""

import atexit
import base64
import hashlib
import logging
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

from happy import paths

log = logging.getLogger("happy.whatsapp")

PORT = int(os.environ.get("WHATSAPP_BRIDGE_PORT") or 3001)
BASE = f"http://127.0.0.1:{PORT}/default"
SERVER = paths.REPO / "whatsapp_server"
DATA = paths.HOME / "whatsapp"
ENV = paths.HOME / "envs" / "whatsapp"
bridge = None


def python():
    exe = ENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    return str(exe) if exe.exists() else None


def wanted():
    return hashlib.sha1((SERVER / "requirements.txt").read_bytes()).hexdigest()[:12]


def installed():
    marker = ENV / ".happy-requirements"
    return python() is not None and marker.exists() and marker.read_text() == wanted()


def install(progress=lambda text: None):
    """Gives the WhatsApp server its own Python, since it needs other library versions than Happy."""
    if installed():
        return True
    uv = shutil.which("uv") or str(Path.home() / ".local" / "bin" / "uv")
    if not Path(uv).exists():
        log.warning("uv is missing, so WhatsApp cannot be installed")
        return False
    progress("Installing WhatsApp")
    if not python():
        subprocess.run([uv, "venv", "-q", "--python", "3.12", str(ENV)], check=True, capture_output=True)
    subprocess.run([uv, "pip", "install", "-q", "-r", str(SERVER / "requirements.txt")], check=True,
                   capture_output=True, env={**os.environ, "VIRTUAL_ENV": str(ENV)})
    (ENV / ".happy-requirements").write_text(wanted())
    return True


def adopt(cfg):
    """Moves a phone already linked by the standalone whatsapp-mcp into Happy, once, so it needs no new scan."""
    if (DATA / "default" / "session.db").exists():
        return False
    named = cfg.get("whatsapp.path") or ""
    for folder in ([Path(named).expanduser()] if named else []) + [paths.REPO.parent / "whatsapp-mcp"]:
        old = folder / "data" / "whatsapp"
        if (old / "default" / "session.db").exists() and not old.is_symlink():
            DATA.parent.mkdir(parents=True, exist_ok=True)
            if DATA.exists() and not any(DATA.iterdir()):
                DATA.rmdir()
            shutil.move(str(old), str(DATA))
            old.symlink_to(DATA, target_is_directory=True)
            for kept in ("facts.pkl", "pending.pkl"):
                if (folder / "data" / kept).exists() and not (DATA / kept).exists():
                    shutil.copy2(folder / "data" / kept, DATA / kept)
            log.info("moved the linked WhatsApp from %s", old)
            return True
    return False


def environment():
    return {"HAPPY_WHATSAPP": str(DATA), "PYTHONPATH": str(paths.REPO)}


def listening():
    with socket.socket() as probe:
        probe.settimeout(0.3)
        return probe.connect_ex(("127.0.0.1", PORT)) == 0


def start_bridge():
    """Starts the bridge unless one is already answering on its port."""
    global bridge
    if listening():
        return True
    if not python():
        return False
    log_file = open(paths.HOME / "whatsapp-bridge.log", "a")
    bridge = subprocess.Popen([python(), "-m", "whatsapp_server.bridge"], cwd=str(paths.REPO),
                              env={**os.environ, **environment()}, stdout=log_file, stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
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


def status():
    """{'linked', 'connected', 'name', 'phone'} from the running bridge, or None when it is not up."""
    try:
        data = httpx.get(f"{BASE}/status", timeout=3).json()
    except (httpx.HTTPError, ValueError):
        return None
    return {"linked": bool(data.get("authenticated")), "connected": bool(data.get("connected")),
            "name": data.get("name") or "", "phone": data.get("phone") or ""}


def qr_code():
    """The QR to scan as PNG bytes, 'linked' once a phone is linked, or None while it is still coming."""
    try:
        httpx.post(f"{BASE}/start", timeout=5)
        data = httpx.get(f"{BASE}/qr", timeout=5).json()
    except (httpx.HTTPError, ValueError):
        return None
    if data.get("status") == "connected":
        return "linked"
    image = data.get("qr") or ""
    return base64.b64decode(image.split(",", 1)[1]) if image.startswith("data:image") else None


def unlink():
    """Logs the phone out and forgets its session, so linking again needs a new scan."""
    try:
        return bool(httpx.post(f"{BASE}/disconnect", timeout=15).json().get("success"))
    except (httpx.HTTPError, ValueError):
        return False


def own_chat():
    """The id of Happy's own WhatsApp group, where the person writes from their phone; None until it is made."""
    from happy.config import Config

    return Config().get("whatsapp.own_chat_id") or None


def spec():
    """How to launch the WhatsApp MCP server, or None until it is installed."""
    if not installed():
        return None
    return {"command": python(), "args": ["-m", "whatsapp_server.server"], "cwd": str(paths.REPO), "env": environment()}
