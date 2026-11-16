"""Learning a way of talking from dialogue, like a show's subtitles, into a short style note."""

import asyncio
import re
import shutil
from pathlib import Path

from happy import paths
from happy.config import Config
from happy.observability import create_posthog_client, new_session_id, new_trace_id

DISTILL = """Here are lines of dialogue. Describe how these characters talk so an assistant can talk the same way.
Write at most 120 words of plain style notes: tone, rhythm, sentence length, typical words and turns of phrase, how they address people.
Then give 6 short example lines in that style that an assistant might say while helping with a computer (like confirming a task or reporting what it found).
Never mention the story, places or character names.

Dialogue:
{lines}"""


def dialogue(text):
    """Dialogue lines out of an .srt, .vtt or plain transcript; prose with no line breaks is split into sentences."""
    if text.count("\n") < 20:
        text = re.sub(r"(?<=[.!?])\s+", "\n", text)
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.isdigit() or "-->" in line or line.upper() == "WEBVTT":
            continue
        line = re.sub(r"<[^>]+>|\{[^}]+\}|\[[^\]]+\]", "", line).strip(" -")
        if line:
            lines.append(line)
    return lines


async def complete(cfg, prompt):
    from happy.agent import choose

    posthog_client = create_posthog_client()
    session_id = new_session_id("persona")
    try:
        if cfg.get("brain.kind") in ("auto", "claude") and choose.claude_ready():
            from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query as claude_query

            query = claude_query
            kwargs = {}
            if posthog_client:
                from posthog.ai.claude_agent_sdk import query

                kwargs = {
                    "posthog_client": posthog_client,
                    "posthog_trace_id": new_trace_id(),
                    "posthog_properties": {"$ai_session_id": session_id},
                    "posthog_privacy_mode": False,
                }
            out = []
            options = ClaudeAgentOptions(tools=[], model="sonnet", setting_sources=[], cli_path=shutil.which("claude"))
            async for message in query(prompt=prompt, options=options, **kwargs):
                if isinstance(message, AssistantMessage):
                    out += [b.text for b in message.content if isinstance(b, TextBlock)]
            return "\n".join(out)
        backend = choose.backend(cfg, posthog_client=posthog_client, ai_session_id=session_id)
        reply = await backend.client.chat.completions.create(
            model=backend.model,
            messages=[{"role": "user", "content": prompt}],
            **backend.ai_call_options(new_trace_id()),
        )
        return reply.choices[0].message.content
    finally:
        if posthog_client:
            try:
                posthog_client.shutdown()
            except Exception:
                pass


FILE = paths.HOME / "persona.md"
# TYPED WORDS UP TO THIS LONG ARE KEPT AS THEY ARE; ANYTHING LONGER IS A PASTE TO LEARN A STYLE FROM.
TYPED = 800
# THE MOST THAT EVER GOES INTO THE PROMPT, WHATEVER WRITES THE FILE.
LONGEST = 1500
# HOW MUCH OF A PASTE THE MODEL READS: SPREAD EVENLY ACROSS IT, FAR UNDER ANY CONTEXT WINDOW.
SAMPLE_LINES = 600
SAMPLE_CHARACTERS = 40_000


def sample(lines):
    """An even spread of the lines, so a ten-million-word paste costs the same as a short one."""
    step = max(1, len(lines) // SAMPLE_LINES)
    picked, size = [], 0
    for line in lines[::step]:
        size += len(line) + 1
        if size > SAMPLE_CHARACTERS:
            break
        picked.append(line[:300])
    return picked


def distilled(text, cfg=None):
    """Short style notes and example lines learned from a long paste, or a few of its own lines when no model answers."""
    lines = sample(dialogue(text))
    try:
        notes = asyncio.run(complete(cfg or Config(), DISTILL.format(lines="\n".join(lines)))).strip()
    except Exception:
        notes = ""
    if not notes:
        notes = "Talk the way these lines do:\n" + "\n".join(lines[:: max(1, len(lines) // 20)][:20])
    return notes


def adopt(text, cfg=None):
    """What was typed or pasted as a way of talking, made small enough for the prompt and saved; returns what was kept."""
    text = (text or "").strip()
    kept = text if len(text) <= TYPED else distilled(text, cfg)
    write(kept)
    return read()


def read():
    """The way of talking Happy uses now, as the person would edit it; empty for his own."""
    return FILE.read_text().strip() if FILE.exists() else ""


def write(text):
    """Saves a way of talking, or with nothing goes back to Happy's own; the next turn uses it."""
    text = (text or "").strip()[:LONGEST]
    if text:
        FILE.parent.mkdir(parents=True, exist_ok=True)
        FILE.write_text(text + "\n")
    else:
        FILE.unlink(missing_ok=True)
    cfg = Config()
    if cfg.get("persona"):
        # THE OLD CONFIG LINE WOULD OTHERWISE SPEAK UP AGAIN ONCE THE FILE IS GONE.
        cfg.set("persona", "")
        cfg.save()


def learn(file):
    cfg = Config()
    source = Path(file).expanduser()
    if not source.exists():
        print(f"No file at {source}.")
        return 1
    lines = dialogue(source.read_text(errors="ignore"))
    if len(lines) < 20:
        print("That file has too little dialogue to learn a style from.")
        return 1
    step = max(1, len(lines) // 600)
    sample = "\n".join(lines[::step][:600])
    print(f"Learning the style from {len(lines)} lines…")
    notes = asyncio.run(complete(cfg, DISTILL.format(lines=sample))).strip()
    FILE.write_text(notes + "\n")
    cfg.set("persona", str(source))
    cfg.save()
    print(f"\n{notes}\n\nSaved to {FILE}. Edit it freely in the settings, under Personality.")
    return 0
