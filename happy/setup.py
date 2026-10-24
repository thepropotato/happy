"""`happy doctor`, `happy persona` and `happy connect mail`, for the terminal."""

import asyncio
import getpass
import imaplib
import re
import shutil
import ssl
import subprocess
import sys
from pathlib import Path

from happy import models, paths
from happy.config import Config, save_secret, secrets

TTY = sys.stdin.isatty()


def ask(question, default=""):
    if not TTY:
        return default
    answer = input(f"{question}{f' [{default}]' if default else ''}: ").strip()
    return answer or default


def yes(question, default=True):
    answer = ask(f"{question} ({'Y/n' if default else 'y/N'})", "")
    return default if not answer else answer.lower().startswith("y")


def heading(text):
    print(f"\n\033[1m{text}\033[0m")


def connect_mail():
    cfg = Config()
    heading("Email")
    print("  Happy reads and sends mail over IMAP with an app password.")
    print("  Gmail: myaccount.google.com/apppasswords · iCloud: account.apple.com · Outlook: account.microsoft.com/security")
    address = ask("Email address", cfg.get("mail.address"))
    if "@" not in address:
        return 1
    password = getpass.getpass("App password (hidden): ").replace(" ", "")
    cfg.set("mail.address", address)
    cfg.save()
    save_secret("mail_password", password)
    from happy.tools.mail import account

    _, _, host, _ = account()
    try:
        box = imaplib.IMAP4_SSL(host, ssl_context=ssl.create_default_context(), timeout=20)
        box.login(address, password)
        box.logout()
        print("  Connected.")
    except Exception as error:
        print(f"  Could not sign in to {host}: {error}")
        return 1
    return 0


def doctor():
    cfg = Config()
    ok = lambda good, text: print(f"  {'✓' if good else '✕'} {text}")
    heading("Happy doctor")
    for name in models.SPEECH:
        ok(models.where(name).exists(), f"{name} model")
    from happy.brain import pick

    kind = cfg.get("brain.kind")
    ok(bool(pick.options()) or bool(cfg.get("brain.base_url")), f"brain: {kind} {cfg.get('brain.model') or ''}".strip())
    try:
        from happy.ears.listen import pick_mic

        index, mic = pick_mic(cfg.get("input.device") or "")
        ok(index is not None, f"microphone: {mic}")
    except Exception as error:
        ok(False, f"microphone: {error}")
    if sys.platform == "darwin":
        from ApplicationServices import AXIsProcessTrusted

        ok(AXIsProcessTrusted(), "Accessibility permission (push-to-talk, typing, clicking)")
    from happy.connectors import inherit, whatsapp

    linked = (whatsapp.status() or {}).get("linked") if whatsapp.listening() else None
    ok(whatsapp.installed(), f"WhatsApp: {'installed' if whatsapp.installed() else 'not installed yet'}" + ("" if linked is None else ", linked" if linked else ", not linked"))
    servers = inherit.everything()
    ok(True, f"MCP servers from other apps: {', '.join(f'{n} ({s})' for n, (_, s) in servers.items()) or 'none'}")
    from happy.tools.handoff import installed

    agents = installed()
    ok(bool(agents), f"coding agents: {', '.join(name for _, name, _ in agents) or 'none installed'}")
    ok(bool(cfg.get("mail.address") and secrets().get("mail_password")), f"email: {cfg.get('mail.address') or 'not connected (happy connect mail)'}")
    return 0


def subtitles(text):
    """Dialogue lines out of an .srt, .vtt or plain transcript."""
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.isdigit() or "-->" in line or line.upper() == "WEBVTT":
            continue
        line = re.sub(r"<[^>]+>|\{[^}]+\}|\[[^\]]+\]", "", line).strip(" -")
        if line:
            lines.append(line)
    return lines


DISTILL = """Here are lines of dialogue. Describe how these characters talk so an assistant can talk the same way.
Write at most 120 words of plain style notes: tone, rhythm, sentence length, typical words and turns of phrase, how they address people.
Then give 6 short example lines in that style that an assistant might say while helping with a computer (like confirming a task or reporting what it found).
Never mention the story, places or character names.

Dialogue:
{lines}"""


async def complete(cfg, prompt):
    from happy.brain import pick

    if (cfg.get("brain.kind") in ("auto", "claude")) and pick.claude_ready():
        from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

        out = []
        async for message in query(prompt=prompt, options=ClaudeAgentOptions(tools=[], model="sonnet", setting_sources=[],
                                                                             cli_path=shutil.which("claude"))):
            if isinstance(message, AssistantMessage):
                out += [b.text for b in message.content if isinstance(b, TextBlock)]
        return "\n".join(out)
    brain = pick.choose(cfg)
    reply = await brain.client.chat.completions.create(model=brain.model, messages=[{"role": "user", "content": prompt}])
    return reply.choices[0].message.content


def persona(file):
    cfg = Config()
    source = Path(file).expanduser()
    if not source.exists():
        print(f"No file at {source}.")
        return 1
    lines = subtitles(source.read_text(errors="ignore"))
    if len(lines) < 20:
        print("That file has too little dialogue to learn a style from.")
        return 1
    step = max(1, len(lines) // 600)
    sample = "\n".join(lines[::step][:600])
    print(f"Learning the style from {len(lines)} lines…")
    notes = asyncio.run(complete(cfg, DISTILL.format(lines=sample))).strip()
    (paths.HOME / "persona.md").write_text(notes + "\n")
    cfg.set("persona", str(source))
    cfg.save()
    print(f"\n{notes}\n\nSaved to {paths.HOME / 'persona.md'}. Edit it freely; restart Happy to use it.")
    return 0
