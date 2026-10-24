"""`happy setup`, `happy doctor`, `happy persona` and `happy connect`: the few questions Happy ever asks."""

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


def choose_brain(cfg):
    from happy.brain import pick

    heading("Brain")
    found = pick.options()
    for number, (_, label, _) in enumerate(found, 1):
        print(f"  {number}. {label}")
    print(f"  {len(found) + 1}. Another service with an API key (OpenAI-compatible URL)")
    picked = ask("Which one", "1") if found else str(len(found) + 1)
    try:
        index = int(picked) - 1
    except ValueError:
        index = 0
    if 0 <= index < len(found):
        kind, label, settings = found[index]
        if kind == "claude":
            cfg.set("brain.kind", "claude")
            cfg.set("brain.model", ask("Claude model (sonnet is the balance of speed and smarts; haiku is fastest)", cfg.get("brain.model") or "sonnet"))
        else:
            cfg.set("brain.kind", "openai")
            cfg.set("brain.base_url", settings["base_url"])
            cfg.set("brain.model", settings["model"])
            if settings.get("key"):
                save_secret("api_key", settings["key"])
        print(f"  Using {label}.")
        return
    url = ask("API URL, the one in the provider's docs (like https://api.openai.com/v1)")
    if not url:
        print("  No brain chosen. Run happy setup again any time.")
        return
    cfg.set("brain.kind", "openai")
    cfg.set("brain.base_url", url.rstrip("/").removesuffix("/chat/completions"))
    cfg.set("brain.model", ask("Model name"))
    key = getpass.getpass("API key (hidden): ") if TTY else ""
    if key:
        save_secret("api_key", key)


def whatsapp_env(folder):
    from happy.connectors import whatsapp

    if whatsapp.python():
        return True
    print("  Installing what the WhatsApp server needs…")
    env = paths.HOME / "envs" / "whatsapp"
    uv = shutil.which("uv")
    if not uv:
        print("  uv is needed for this: https://docs.astral.sh/uv/")
        return False
    subprocess.run([uv, "venv", "-q", "--python", "3.12", str(env)], check=True)
    subprocess.run([uv, "pip", "install", "-q", "-r", str(Path(folder) / "requirements.txt")], check=True,
                   env={**__import__("os").environ, "VIRTUAL_ENV": str(env)})
    return True


def connect(what):
    cfg = Config()
    if what == "mail":
        heading("Email")
        print("  Happy reads and sends mail over IMAP with an app password.")
        print("  Gmail: myaccount.google.com/apppasswords · iCloud: account.apple.com · Outlook: account.microsoft.com/security")
        address = ask("Email address", cfg.get("mail.address"))
        if not address:
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
    from happy.connectors import whatsapp

    heading("WhatsApp")
    folder = whatsapp.root(cfg)
    if not folder:
        named = ask("Where is the whatsapp-mcp folder")
        if not named or not Path(named).expanduser().exists():
            print("  WhatsApp needs the whatsapp-mcp server folder.")
            return 1
        cfg.set("whatsapp.path", str(Path(named).expanduser()))
        cfg.save()
        folder = whatsapp.root(cfg)
    if not whatsapp_env(folder):
        return 1
    print(f"  Using {folder}. If this phone was never linked, ask Happy to show the WhatsApp QR code.")
    return 0


def main():
    cfg = Config()
    print("\033[1mSetting up Happy\033[0m — a voice agent that lives on this computer.")
    heading("Speech models")
    models.ensure()
    print("  Loading the voice once so it starts fast later…")
    from happy.voice.speaker import Speaker

    speaker = Speaker(cfg.get("voice") or "alba")
    try:
        speaker.start()
    except Exception as error:
        print(f"  The voice did not load: {error}")
    choose_brain(cfg)
    heading("Name")
    name = ask("What should it be called? Saying the name wakes it", cfg.get("name"))
    cfg.set("name", name.strip().title() or "Happy")
    from happy.connectors import whatsapp

    folder = whatsapp.root(cfg)
    if folder and yes(f"\nFound a WhatsApp server at {folder}. Use it?"):
        cfg.set("whatsapp.path", str(folder))
        whatsapp_env(folder)
    cfg.save()
    if not cfg.get("mail.address") and yes("\nConnect an email account?", default=False):
        connect("mail")
    permissions()
    heading("Done")
    print("  Start it with:  happy          (or happy start to run it in the background)")
    print(f"  Hold {cfg.get('push_to_talk').replace('_', ' ')} to talk, or say “{cfg.get('name')}”.")
    return 0


def permissions():
    if sys.platform != "darwin":
        return
    heading("Permissions")
    print("  macOS will ask for these the first time each is needed. Grant them to the terminal you run Happy from:")
    print("  • Microphone — to hear you")
    print("  • Accessibility — for the push-to-talk key, typing and clicking")
    print("  • Screen Recording — so it can look at the screen when you ask")
    print("  • Automation — to work Chrome, Safari, Finder and Terminal")
    from ApplicationServices import AXIsProcessTrustedWithOptions

    AXIsProcessTrustedWithOptions({"AXTrustedCheckOptionPrompt": True})


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

    folder = whatsapp.root(cfg)
    ok(bool(folder and whatsapp.python()), f"WhatsApp server: {folder or 'not found'}")
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
