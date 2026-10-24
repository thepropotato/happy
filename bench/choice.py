"""Scores which tool a brain picks for requests the fast path does not catch, with every tool mocked."""

import asyncio
import json
import os
import sys
import time

os.environ.setdefault("HAPPY_HOME", "/tmp/happy-bench")

from happy import tools
from happy.brain import Act, Problem, Text
from happy.config import Config

CASES = [
    ("open the happy project in vs code", "open_file", {"app": "code"}),
    ("show me my resume in finder", "open_file", {"app": "finder"}),
    ("what's on my screen right now", "look_at_screen", {}),
    ("close all the youtube tabs", "browser_tabs", {"action": "close", "match": "youtube"}),
    ("switch to the gmail tab", "browser_tabs", {"action": "switch", "match": "gmail"}),
    ("summarise this article for me", "read_tab", {}),
    ("do I have any new whatsapp messages", "whatsapp_unread", {}),
    ("what did ravi say on whatsapp", "whatsapp_read", {"chat": "ravi"}),
    ("find the address I sent to my brother on whatsapp", "whatsapp_find", {"what": "address"}),
    ("tell mom on whatsapp that I'll be home by eight", "whatsapp_send", {"to": "mom"}),
    ("read my latest emails", "check_mail", {}),
    ("build me a small snake game in python", "hand_off_coding", {}),
    ("fix the failing tests in the open slate project", "hand_off_coding", {"folder": "open slate"}),
    ("open youtube and search for lofi music", "open_link", {}),
    ("set the brightness a little lower, like thirty", "set_brightness", {"percent": 30}),
    ("it's too loud", "set_volume", {}),
    ("press command shift t", "press_keys", {}),
    ("remember that my brother's name on whatsapp is Ravi Anna", "remember", {}),
    ("where's the pdf my boss sent me last week on whatsapp", "whatsapp_search", {"kind": "document"}),
    ("is anything playing right now? pause it", "media", {"action": "pause"}),
]

CANNED = {
    "whatsapp_unread": "2 unread messages in 1 chats:\nRavi Anna: 2 unread, last from Ravi Anna: are you coming tomorrow?",
    "whatsapp_read": "[Fri 23 Oct, 9:10 PM] Ravi Anna: did you reach?\n[Fri 23 Oct, 9:12 PM] Me: yes reached",
    "whatsapp_find": "Best matches out of 812 messages:\n[Mon 2 Mar, 4:01 PM in Ravi Anna] Me: Flat 402, Sai Residency, Road no 5, Banjara Hills, Hyderabad 500034",
    "check_mail": "#812 from GitHub <noreply@github.com>, Sat 24 Oct, 2:10 PM: [open-slate] PR merged — Your pull request was merged.",
    "look_at_screen": "Front app: Google Chrome\nWindow: Lofi Girl - YouTube\nGoogle Chrome tab in front: Lofi Girl - YouTube — https://www.youtube.com/watch?v=jfKfPfyJRdk",
    "read_tab": "Why sleep matters — https://example.com/sleep\n\nSleep consolidates memory and clears waste from the brain. Adults need 7 to 9 hours.",
}


async def main(base_url, model):
    tools.load()
    for registered in tools.REGISTRY.values():
        registered.needs = None
    picked = []

    async def fake(name, args):
        picked.append((name, args))
        return CANNED.get(name, "Done.")

    tools.call = fake
    from happy.brain import local

    local.tools.call = fake
    brain = local.Local(Config(), base_url, model)
    await brain.start()
    score, rows = 0, []
    for text, want, want_args in CASES:
        picked.clear()
        await brain.reset()
        started, first, spoken = time.monotonic(), None, []

        def emit(event):
            nonlocal first
            if first is None and isinstance(event, (Text, Act)):
                first = time.monotonic() - started
            if isinstance(event, Text):
                spoken.append(event.delta)
            if isinstance(event, Problem):
                spoken.append(f"[problem: {event.message}]")

        await brain.turn(text, emit)
        took = time.monotonic() - started
        chosen = picked[0] if picked else (None, {})
        right = chosen[0] == want and all(str(v).lower() in json.dumps(chosen[1]).lower() for v in want_args.values())
        score += right
        rows.append(f"{'✓' if right else '✗'} {took:5.1f}s first {first or 0:4.1f}s  {text!r} -> {chosen[0]} {json.dumps(chosen[1])[:90]} | said: {''.join(spoken)[:90]!r}")
        print(rows[-1], flush=True)
    print(f"\n{model}: {score}/{len(CASES)}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:11434/v1",
                     sys.argv[2] if len(sys.argv) > 2 else "gpt-oss:20b"))
