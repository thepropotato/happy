"""Learning a way of talking from dialogue, like a show's subtitles, into a short style note."""

import asyncio
import re
import shutil
from pathlib import Path

from happy import paths
from happy.config import Config

DISTILL = """Here are lines of dialogue. Describe how these characters talk so an assistant can talk the same way.
Write at most 120 words of plain style notes: tone, rhythm, sentence length, typical words and turns of phrase, how they address people.
Then give 6 short example lines in that style that an assistant might say while helping with a computer (like confirming a task or reporting what it found).
Never mention the story, places or character names.

Dialogue:
{lines}"""


def dialogue(text):
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


async def complete(cfg, prompt):
    from happy.agent import choose

    if cfg.get("brain.kind") in ("auto", "claude") and choose.claude_ready():
        from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

        out = []
        options = ClaudeAgentOptions(tools=[], model="sonnet", setting_sources=[], cli_path=shutil.which("claude"))
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                out += [b.text for b in message.content if isinstance(b, TextBlock)]
        return "\n".join(out)
    backend = choose.backend(cfg)
    reply = await backend.client.chat.completions.create(model=backend.model, messages=[{"role": "user", "content": prompt}])
    return reply.choices[0].message.content


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
    (paths.HOME / "persona.md").write_text(notes + "\n")
    cfg.set("persona", str(source))
    cfg.save()
    print(f"\n{notes}\n\nSaved to {paths.HOME / 'persona.md'}. Edit it freely; restart Happy to use it.")
    return 0
