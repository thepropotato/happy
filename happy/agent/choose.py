"""Chooses the brain from what this computer already has: Claude Code, an API key, Ollama or LM Studio."""

import json
import os
import shutil
from pathlib import Path

import httpx

from happy.config import secrets

HOSTED = {
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY", "gpt-5-mini"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "openai/gpt-oss-120b"),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "openai/gpt-oss-120b"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY", "gemini-2.5-flash"),
}
OLLAMA = "http://localhost:11434"
LMSTUDIO = "http://localhost:1234/v1"


def claude_ready():
    if not shutil.which("claude"):
        return False
    if os.environ.get("ANTHROPIC_API_KEY"):
        return True
    try:
        return bool(json.loads((Path.home() / ".claude.json").read_text()).get("oauthAccount"))
    except (OSError, ValueError):
        return False


def ollama_models():
    """Ollama models that can call tools, biggest first."""
    try:
        listed = httpx.get(f"{OLLAMA}/api/tags", timeout=2).json().get("models", [])
    except (httpx.HTTPError, ValueError):
        return []
    usable = []
    for model in listed:
        try:
            shown = httpx.post(f"{OLLAMA}/api/show", json={"model": model["name"]}, timeout=5).json()
        except (httpx.HTTPError, ValueError):
            continue
        if "tools" in (shown.get("capabilities") or []):
            usable.append((model.get("size", 0), model["name"]))
    return [name for _, name in sorted(usable, reverse=True)]


def lmstudio_models():
    try:
        return [m["id"] for m in httpx.get(f"{LMSTUDIO}/models", timeout=2).json().get("data", [])
                if "embed" not in m["id"]]
    except (httpx.HTTPError, ValueError, KeyError):
        return []


def options():
    """Every brain this computer could use right now, best first, as (kind, label, settings)."""
    found = []
    if claude_ready():
        found.append(("claude", "Claude, through your Claude Code login", {}))
    stored = secrets()
    for kind, (url, env, model) in HOSTED.items():
        key = os.environ.get(env) or stored.get(env.lower())
        if key:
            found.append(("openai", f"{kind.title()} ({model}) with your API key", {"base_url": url, "model": model, "key": key, "local": False}))
    for model in ollama_models():
        found.append(("openai", f"Ollama: {model}", {"base_url": f"{OLLAMA}/v1", "model": model, "local": True}))
    for model in lmstudio_models():
        found.append(("openai", f"LM Studio: {model}", {"base_url": LMSTUDIO, "model": model, "local": True}))
    return found


def backend(cfg, extra_servers=None):
    """The brain named in the config, or the best one found."""
    kind = cfg.get("brain.kind") or "auto"
    if kind == "claude" or (kind == "auto" and claude_ready()):
        from happy.agent.claude import Claude

        return Claude(cfg, extra_servers)
    from happy.agent.openai_compatible import OpenAICompatible

    if cfg.get("brain.base_url"):
        url = cfg.get("brain.base_url")
        key = secrets().get("api_key") or ""
        local = "localhost" in url or "127.0.0.1" in url
        return OpenAICompatible(cfg, url, cfg.get("brain.model"), key, local=local)
    for found_kind, _, settings in options():
        if found_kind == "openai":
            return OpenAICompatible(cfg, settings["base_url"], settings["model"], settings.get("key", ""), local=settings["local"])
    return None
