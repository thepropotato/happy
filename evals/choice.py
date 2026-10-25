"""Scores which tool a backend picks for requests the fast path does not catch, with every tool mocked."""

import asyncio
import json
import os
import sys
import time

os.environ.setdefault("HAPPY_HOME", "/tmp/happy-bench")

from happy import tools
from happy.agent import Act, Problem, Text, quick
from happy.config import Config

CASES = [
    ("open the happy project in vs code", "open_file", {"app": "code"}),
    ("show me my resume in finder", "open_file", {"app": "finder"}),
    ("what's on my screen right now", "look_at_screen", {}),
    ("close all the youtube tabs", "browser_tabs", {"action": "close", "match": "youtube"}),
    ("switch to the gmail tab", "browser_tabs", {"action": "switch", "match": "gmail"}),
    ("summarise this article for me", "read_tab", {}),
    ("do I have any new whatsapp messages", "whatsapp_unread", {}),
    ("what did ravi say on whatsapp", ("whatsapp_read", "whatsapp_search"), {"chat": "ravi"}),
    ("find the address I sent to my brother on whatsapp", "whatsapp_find", {"what": "address"}),
    ("tell mom on whatsapp that I'll be home by eight", "whatsapp_send", {"to": "mom"}),
    ("read my latest emails", "gmail__search_threads", {}),
    ("build me a small snake game in python", "hand_off_coding", {}),
    ("fix the failing tests in the open slate project", "hand_off_coding", {"folder": "open slate"}),
    ("open youtube and search for lofi music", "open_link", {}),
    ("set the brightness a little lower, like thirty", "set_brightness", {"level": 30}),
    ("can you make the screen a little less bright", "set_brightness", {"change": "down"}),
    ("it's too loud", "set_volume", {}),
    ("press command shift t", "press_keys", {}),
    ("remember that my brother's name on whatsapp is Ravi Anna", "remember", {}),
    ("where's the pdf my boss sent me last week on whatsapp", ("whatsapp_search", "whatsapp_find"), {}),
    ("is anything playing right now? pause it", "media", {"action": "pause"}),
    ("is my email connected?", "connections", {}),
    ("is the email MCP connected", "connections", {}),
    ("can you tell me whether my mail thing is hooked up to you", "connections", {}),
    ("which of my MCP servers are working", "connections", {}),
    ("do you have access to my linear account", "connections", {}),
    ("check my email", "gmail__search_threads", {}),
    ("draft an email to ravi saying I'll call him tonight", "gmail__create_draft", {}),
    ("I want you to search for the current price of PS5 in India.", "web_search", {"query": "ps5"}),
    ("what's the weather going to be like in hyderabad tomorrow", "web_search", {"query": "hyderabad"}),
    ("who won the formula one race last weekend", "web_search", {}),
    ("look up how many calories are in a dosa", "web_search", {"query": "dosa"}),
    ("google the release date of GTA 6", "web_search", {"query": "gta"}),
    ("open flipkart and show me the ps5 listings", "open_link", {"where": "flipkart"}),
]

GMAIL = [
    ("gmail__search_threads", "From the gmail service: Search Gmail threads with a Gmail search query, newest first.",
     {"query": {"type": "string"}, "max_results": {"type": "integer"}}, []),
    ("gmail__get_thread", "From the gmail service: Get one Gmail thread and all its messages.", {"thread_id": {"type": "string"}}, ["thread_id"]),
    ("gmail__create_draft", "From the gmail service: Create a draft email for the person to review and send.",
     {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}, ["to", "body"]),
]

CANNED = {
    "whatsapp_unread": "2 unread messages in 1 chats:\nRavi Anna: 2 unread, last from Ravi Anna: are you coming tomorrow?",
    "whatsapp_read": "[Fri 23 Oct, 9:10 PM] Ravi Anna: did you reach?\n[Fri 23 Oct, 9:12 PM] Me: yes reached",
    "whatsapp_find": "Best matches out of 812 messages:\n[Mon 2 Mar, 4:01 PM in Ravi Anna] Me: Flat 402, Sai Residency, Road no 5, Banjara Hills, Hyderabad 500034",
    "look_at_screen": "Front app: Google Chrome\nWindow: Lofi Girl - YouTube\nGoogle Chrome tab in front: Lofi Girl - YouTube — https://www.youtube.com/watch?v=jfKfPfyJRdk",
    "connections": "Internet: online\nModel: gpt-oss:20b\nWhatsApp: connected (linked as Venu)\nEmail through gmail (from Claude Code): connected (9 tools)\nMCP server linear (from Claude Code): needs sign-in (401 Unauthorized)\nMCP server freecad (from Claude Code): connected (14 tools)",
    "gmail__search_threads": "thread 18c2a (Sat 24 Oct, 2:10 PM) GitHub <noreply@github.com>: [open-slate] PR merged\nthread 18c1f (Fri 23 Oct) Priya: Dinner on Sunday?",
    "gmail__create_draft": "Draft created: id r-551, to ravi@example.com.",
    "find_files": "/Users/venupulagam/Desktop/projects/open-slate (changed 14 Oct 2026)\n/Users/venupulagam/Documents/Resume 2026.pdf (changed 02 Sep 2026)",
    "open_file": "Opened /Users/venupulagam/Documents/Resume 2026.pdf in Finder.",
    "hand_off_coding": "Opened Claude Code in a Terminal window in /Users/venupulagam/Desktop/projects/open-slate with the task.",
    "whatsapp_search": "[Mon 19 Oct, 10:02 AM in Office] Suresh (boss): [document] (file Q3-plan.pdf)",
    "web_search": "1. Sony PlayStation5 Online in India at Best Prices - Flipkart — www.flipkart.com\n   The PS5 gaming console delivers eye-catching graphics with hardware that supports ray tracing.\n"
                  "2. Amazon.in: Ps5 — www.amazon.in\n   Discover a wide selection of PS5 games, consoles, and gaming accessories.\n"
                  "3. Sony PS5 Consoles | Reliance Digital — www.reliancedigital.in\n   Compare Slim, Digital, & Disc Models.\n\n"
                  "The snippets are short; read_result reads a whole page.",
    "read_tab": "Why sleep matters — https://example.com/sleep\n\nSleep consolidates memory and clears waste from the backend. Adults need 7 to 9 hours.",
}


async def main(base_url, model):
    tools.load()
    for registered in tools.REGISTRY.values():
        registered.needs = None
    for name, description, props, required in GMAIL:
        schema = {"type": "object", "properties": props, "required": required}
        tools.REGISTRY[name] = tools.Tool(name=name, fn=None, description=description, schema=schema,
                                          label=name, local_only=True, params=props)
    picked = []

    async def fake(name, args):
        picked.append((name, args))
        return CANNED.get(name, "Done.")

    tools.call = fake
    from happy.agent import openai_compatible

    openai_compatible.tools.call = fake
    backend = openai_compatible.OpenAICompatible(Config(), base_url, model)
    await backend.start()
    score, rows = 0, []
    for text, want, want_args in CASES:
        picked.clear()
        await backend.reset()
        started, first, spoken = time.monotonic(), None, []

        def emit(event):
            nonlocal first
            if first is None and isinstance(event, (Text, Act)):
                first = time.monotonic() - started
            if isinstance(event, Text):
                spoken.append(event.delta)
            if isinstance(event, Problem):
                spoken.append(f"[problem: {event.message}]")

        fast = quick.match(text)
        if fast:
            picked.append(fast)
            spoken.append("(fast path)")
        else:
            await backend.turn(text, emit)
        took = time.monotonic() - started
        wanted = want if isinstance(want, tuple) else (want,)
        hits = [c for c in picked if c[0] in wanted and all(str(v).lower() in json.dumps(c[1]).lower() for v in want_args.values())]
        right = bool(hits)
        chosen = hits[0] if hits else (picked[0] if picked else (None, {}))
        score += right
        trail = " → ".join(c[0] for c in picked)
        rows.append(f"{'✓' if right else '✗'} {took:5.1f}s first {first or 0:4.1f}s  {text!r} -> {trail} {json.dumps(chosen[1])[:80]} | said: {''.join(spoken)[:90]!r}")
        print(rows[-1], flush=True)
    print(f"\n{model}: {score}/{len(CASES)}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:11434/v1",
                     sys.argv[2] if len(sys.argv) > 2 else "gpt-oss:20b"))
