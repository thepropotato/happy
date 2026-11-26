"""Whether a brain can think right now, and when it cannot, why in plain words and the one thing that fixes it.

The settings ask `check` when a brain is picked; the brains pass their errors through `explain` while Happy runs, so
"out of credits" reads the same in both places.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpx

PROBE = "Reply with the single word OK."
CLAUDE_INSTALL = "https://claude.ai/install.ps1" if sys.platform == "win32" else "https://claude.ai/install.sh"
# WHERE EACH HOSTED SERVICE TAKES PAYMENT AND KEYS, FOR THE BUTTON THAT FIXES "NO CREDITS" OR "WRONG KEY".
BILLING = {"api.openai.com": "https://platform.openai.com/settings/organization/billing",
           "openrouter.ai": "https://openrouter.ai/settings/credits",
           "api.groq.com": "https://console.groq.com/settings/billing",
           "generativelanguage.googleapis.com": "https://aistudio.google.com/apikey",
           "api.anthropic.com": "https://console.anthropic.com/settings/billing"}
KEYS = {"api.openai.com": "https://platform.openai.com/api-keys", "openrouter.ai": "https://openrouter.ai/settings/keys",
        "api.groq.com": "https://console.groq.com/keys", "generativelanguage.googleapis.com": "https://aistudio.google.com/apikey",
        "api.anthropic.com": "https://console.anthropic.com/settings/keys"}
LOCAL = {"11434": ("Ollama", "https://ollama.com/download"), "1234": ("LM Studio", "https://lmstudio.ai")}
# THE LAST PROBLEM A BRAIN HIT WHILE HAPPY RAN, SO THE SETTINGS SHOW IT AND ITS FIX UNTIL A CHECK PASSES.
latest = None


@dataclass
class Verdict:
    state: str  # ready, checking, not_installed, signed_out, no_credits, limit, bad_key, unreachable, no_model, failed
    text: str = ""
    action: dict = field(default_factory=dict)  # {"label", "do": "claude_login" | "claude_install" | "open", "url"}

    @property
    def ok(self):
        return self.state == "ready"

    def shown(self):
        return asdict(self)


def quiet():
    """Keeps a console program from opening a window of its own when Happy, a windowless app, starts it on Windows."""
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}


def claude_cli():
    return shutil.which("claude") or next((str(p) for p in (Path.home() / ".local" / "bin" / "claude",
                                                             Path.home() / ".local" / "bin" / "claude.exe") if p.exists()), None)


def claude_status():
    """Claude Code's own account of itself: {"installed", "logged_in", "method", "plan"}."""
    cli = claude_cli()
    if not cli:
        return {"installed": False, "logged_in": False, "method": "", "plan": ""}
    if os.environ.get("ANTHROPIC_API_KEY"):
        return {"installed": True, "logged_in": True, "method": "api key", "plan": ""}
    try:
        done = subprocess.run([cli, "auth", "status", "--json"], capture_output=True, text=True, timeout=20,
                              stdin=subprocess.DEVNULL, **quiet())
        status = json.loads(done.stdout)
        return {"installed": True, "logged_in": bool(status.get("loggedIn")), "method": status.get("authMethod") or "",
                "plan": status.get("subscriptionType") or ""}
    except (OSError, subprocess.SubprocessError, ValueError):
        # AN OLDER CLAUDE CODE WITHOUT `auth status`: ITS SAVED LOGIN IS THE NEXT BEST SIGN.
        try:
            saved = json.loads((Path.home() / ".claude.json").read_text(encoding="utf-8"))
            return {"installed": True, "logged_in": bool(saved.get("oauthAccount")), "method": "", "plan": ""}
        except (OSError, ValueError):
            return {"installed": True, "logged_in": False, "method": "", "plan": ""}


def host(url):
    match = re.match(r"https?://([^/:]+)(?::(\d+))?", url or "")
    return (match.group(1), match.group(2) or "") if match else ("", "")


def service_name(url):
    name, port = host(url)
    if name in ("localhost", "127.0.0.1") and port in LOCAL:
        return LOCAL[port][0]
    return {"api.openai.com": "OpenAI", "openrouter.ai": "OpenRouter", "api.groq.com": "Groq",
            "generativelanguage.googleapis.com": "Gemini", "api.anthropic.com": "Anthropic"}.get(name, name or "the service")


def explain(message, kind="claude", url=""):
    """A brain's error, as a Verdict a person can act on."""
    text = str(message or "").strip()
    low = text.lower()
    if kind == "claude":
        who, billing, keys = "Claude", "https://claude.ai/settings/usage", ""
    else:
        who = service_name(url)
        billing, keys = BILLING.get(host(url)[0], ""), KEYS.get(host(url)[0], "")
    if kind == "claude" and re.search(r"not logged in|/login|please log in|oauth token|token (has )?expired|authentication_error|invalid bearer", low):
        return Verdict("signed_out", "Happy isn't signed in to Claude.", {"label": "Sign in to Claude", "do": "claude_login"})
    if re.search(r"credit balance|insufficient_quota|insufficient credits|out of credits|billing|payment required|exceeded your current quota|\b402\b", low):
        return Verdict("no_credits", f"{who} is out of credits.",
                       {"label": "Add credits", "do": "open", "url": billing} if billing else {})
    if re.search(r"usage limit|limit reached|rate limit|rate_limit|too many requests|\b429\b|overloaded|resets? (at|in)", low):
        return Verdict("limit", f"{who} has hit its usage limit for now. It works again once the limit resets.",
                       {"label": "See usage", "do": "open", "url": billing} if billing else {})
    if re.search(r"invalid api key|incorrect api key|invalid_api_key|api key not valid|unauthori[sz]ed|\b401\b|\b403\b|permission denied", low):
        if kind == "claude":
            return Verdict("signed_out", "Claude didn't accept Happy's sign-in.", {"label": "Sign in to Claude", "do": "claude_login"})
        return Verdict("bad_key", f"{who} didn't accept the API key.", {"label": "Get a key", "do": "open", "url": keys} if keys else {})
    if re.search(r"model .*(not found|does not exist|not available)|no such model|unknown model|model_not_found|\b404\b", low):
        return Verdict("no_model", f"{who} doesn't have that model. Pick another one.")
    if re.search(r"connect|connection refused|timed out|timeout|name or service not known|nodename|unreachable|network", low):
        name, port = host(url)
        if kind != "claude" and name in ("localhost", "127.0.0.1") and port in LOCAL:
            app, download = LOCAL[port]
            return Verdict("unreachable", f"{app} isn't running. Open it, then check again.", {"label": f"Get {app}", "do": "open", "url": download})
        return Verdict("unreachable", f"Couldn't reach {who}. Check the internet connection, then check again.")
    return Verdict("failed", f"{who} didn't answer: {text[:160]}" if text else f"{who} didn't answer.")


def check_claude(model="sonnet"):
    """Installed, signed in, and actually answering: the last needs a one-word request, which is how credits show."""
    status = claude_status()
    if not status["installed"]:
        return Verdict("not_installed", "Claude Code isn't installed. Happy uses it to think with Claude.",
                       {"label": "Install Claude Code", "do": "claude_install"})
    if not status["logged_in"]:
        return Verdict("signed_out", "Happy isn't signed in to Claude yet.", {"label": "Sign in to Claude", "do": "claude_login"})
    try:
        done = subprocess.run([claude_cli(), "-p", PROBE, "--output-format", "json", "--model", model or "sonnet"],
                              capture_output=True, text=True, timeout=90, stdin=subprocess.DEVNULL, **quiet())
        reply = json.loads(done.stdout.strip().splitlines()[-1])
    except subprocess.TimeoutExpired:
        return Verdict("unreachable", "Claude took too long to answer. Check the internet connection, then check again.")
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return explain(done.stderr if "done" in locals() else "")
    if reply.get("is_error"):
        return explain(reply.get("result") or reply.get("subtype"))
    return Verdict("ready", f"Claude is ready{' on your ' + status['plan'].title() + ' plan' if status['plan'] else ''}.")


def check_service(url, model, key="", local=False):
    """One tiny request to an OpenAI-shaped service, read for the usual ways it says no."""
    url = (url or "").rstrip("/")
    try:
        reply = httpx.post(f"{url}/chat/completions", timeout=60 if local else 30,
                           headers={"Authorization": f"Bearer {key}"} if key else {},
                           json={"model": model, "messages": [{"role": "user", "content": PROBE}]})
    except httpx.HTTPError as error:
        return explain(f"connection failed: {error}", "openai", url)
    if reply.status_code == 200:
        return Verdict("ready", f"{service_name(url)} is ready with {model}.")
    try:
        body = reply.json()
        detail = body.get("error", body) if isinstance(body, dict) else body
        detail = detail.get("message", "") + " " + str(detail.get("code") or detail.get("type") or "") if isinstance(detail, dict) else str(detail)
    except ValueError:
        detail = reply.text[:300]
    return explain(f"{reply.status_code} {detail}", "openai", url)


def install_claude():
    """Claude Code's own installer, run with no window; True once `claude` is there."""
    if sys.platform == "win32":
        command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", f"irm {CLAUDE_INSTALL} | iex"]
    else:
        command = ["/bin/bash", "-c", f"curl -fsSL {CLAUDE_INSTALL} | bash"]
    try:
        subprocess.run(command, capture_output=True, timeout=600, stdin=subprocess.DEVNULL, **quiet())
    except (OSError, subprocess.SubprocessError):
        return False
    return claude_cli() is not None


def login_claude():
    """Claude Code's sign-in, which opens the browser and waits for it to come back; True once signed in."""
    cli = claude_cli()
    if not cli:
        return False
    try:
        subprocess.run([cli, "auth", "login", "--claudeai"], capture_output=True, timeout=600, stdin=subprocess.DEVNULL, **quiet())
    except (OSError, subprocess.SubprocessError):
        pass
    return claude_status()["logged_in"]
