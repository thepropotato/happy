"""Opt-in, anonymous counts of how each turn went, sent to PostHog to make Happy better; never words, replies, arguments, files or names."""

import json
import logging
import platform
import sys
import threading
import uuid

import httpx

from happy import paths

log = logging.getLogger("happy.usage")

# A POSTHOG PROJECT KEY IS MEANT TO SHIP IN CLIENTS: IT CAN ONLY ADD EVENTS, NEVER READ THEM.
KEY = "phc_piobXG4BAFJiHMwUjy4Gvx2ZwGxaCW5z5oLza2QN4UDy"
URL = "https://us.i.posthog.com/i/v0/e/"
ID = paths.HOME / "usage-id"
LAST = paths.HOME / "usage-last.json"


def install_id():
    """A random id for this computer, so counts can be grouped without knowing whose they are."""
    try:
        return ID.read_text().strip()
    except OSError:
        pass
    made = uuid.uuid4().hex
    try:
        ID.parent.mkdir(parents=True, exist_ok=True)
        ID.write_text(made)
    except OSError:
        pass
    return made


def version():
    from importlib.metadata import PackageNotFoundError, version as installed

    try:
        return installed("happy")
    except PackageNotFoundError:
        return "unknown"


def facts(how, path, steps, seconds, failed, silent, model):
    """What a turn is reduced to: how it was asked, which tools ran and how it ended, and nothing anyone said."""
    # IMPORTED HERE, NOT AT THE TOP: A TOP-LEVEL IMPORT BETWEEN TOOL MODULES REORDERS THE TOOL LIST.
    from happy.tools import REGISTRY

    # HAPPY'S OWN TOOLS AND ITS BUNDLED WHATSAPP KEEP THEIR NAMES; A SERVER THE PERSON ADDED COULD NAME THEM, SO IT IS JUST "mcp".
    def known(name):
        return name in REGISTRY or str(name).startswith("whatsapp_")

    tools = [(step.get("tool") if known(step.get("tool")) else "mcp", step.get("ok") is not False) for step in steps]
    return {
        "how": how,
        "path": path,
        "seconds": round(seconds or 0.0, 1),
        "failed": bool(failed),
        "silent": bool(silent),
        "corrected": how == "correction",
        "tools": [name for name, _ in tools],
        "tool_count": len(tools),
        "tools_failed": sum(1 for _, ok in tools if not ok),
        "model": (model or "")[:40],
        "os": sys.platform,
        "os_version": platform.release(),
        "version": version(),
        # ANONYMOUS EVENTS: NO PERSON PROFILE, AND NO LOCATION WORKED OUT FROM THE ADDRESS.
        "$process_person_profile": False,
        "$geoip_disable": True,
    }


def turn(cfg, **given):
    """Sends one finished turn when sharing is switched on, in the background so a turn never waits on it."""
    if cfg.get("share_usage") is not True:
        return
    try:
        body = {"api_key": KEY, "event": "turn", "distinct_id": install_id(), "properties": facts(**given)}
    except Exception:
        log.debug("could not describe the turn", exc_info=True)
        return
    try:
        LAST.write_text(json.dumps(body["properties"], indent=2))
    except OSError:
        pass
    threading.Thread(target=send, args=(body,), name="usage", daemon=True).start()


def send(body):
    try:
        httpx.post(URL, json=body, timeout=5)
    except httpx.HTTPError as error:
        log.debug("usage not sent: %s", error)


def last():
    """The properties of the last turn sent, for the settings to show; None before there has been one."""
    try:
        return json.loads(LAST.read_text())
    except (OSError, ValueError):
        return None
