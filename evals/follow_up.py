"""Scores whether a correction right after a fast-path answer is taken as a retry, not a fact to remember."""

import asyncio
import json
import os
import sys
import time

os.environ.setdefault("HAPPY_HOME", "/tmp/happy-bench")

from happy import tools
from happy.agent import Text
from happy.config import Config

# AS THE FAST PATH ANSWERS A PLACE NEITHER THE SOUND MATCH NOR THE SEARCH FOUND.
ASKED = "Hey, How's the weather in Lesta currently?"
MISSED = "I couldn't find a place called lesta."
CASES = [
    "It's Lester.",
    "It's Leicester.",
    "L E I C E S T E R",
    "no, Leicester in England",
]
FOUND = ("Leicester, England, United Kingdom, now: light showers, 25°C (feels like 25°C), humidity 94%, wind 41 km/h. "
         "Today: high 26°C, low 24°C, 100% chance of rain.")


async def main(base_url, model, told):
    tools.load()
    for registered in tools.REGISTRY.values():
        registered.needs = None
    picked = []

    async def fake(name, args):
        picked.append((name, args))
        return FOUND if name == "weather" else "Remembered." if name == "remember" else "Done."

    tools.call = fake
    from happy.agent import openai_compatible

    openai_compatible.tools.call = fake
    backend = openai_compatible.OpenAICompatible(Config(), base_url, model)
    await backend.start()
    score = 0
    for text in CASES:
        picked.clear()
        await backend.reset()
        if told:
            backend.heard(ASKED, MISSED)
        spoken, started = [], time.monotonic()
        await backend.turn(text, lambda e: spoken.append(e.delta) if isinstance(e, Text) else None)
        right = any(n == "weather" for n, _ in picked) and not any(n == "remember" for n, _ in picked)
        score += right
        trail = " → ".join(f"{n} {json.dumps(a)}" for n, a in picked)
        print(f"{'✓' if right else '✗'} {time.monotonic() - started:5.1f}s  {text!r} -> {trail} | said: {''.join(spoken)[:80]!r}", flush=True)
    print(f"\n{model} ({'told' if told else 'not told'} of the fast-path turn): {score}/{len(CASES)}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:11434/v1",
                     sys.argv[2] if len(sys.argv) > 2 else "gpt-oss:20b", os.environ.get("TOLD", "1") == "1"))
