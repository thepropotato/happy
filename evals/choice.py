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
    ("what did john say on whatsapp", ("whatsapp_read", "whatsapp_search"), {"chat": "john"}),
    ("any word from jane doe?", ("whatsapp_read", "whatsapp_search"), {"chat": "jane"}),
    ("has jane replied yet", ("whatsapp_read", "whatsapp_search"), {"chat": "jane"}),
    ("find the address I sent to my brother on whatsapp", "whatsapp_find", {"what": "address"}),
    ("tell mom on whatsapp that I'll be home by eight", "whatsapp_send", {"to": "mom"}),
    ("read my latest emails", ("gmail__search_threads", "account_connector"), {}),
    ("build me a small snake game in python", "hand_off_coding", {}),
    ("fix the failing tests in the open slate project", "hand_off_coding", {"folder": "open slate"}),
    ("can you ask claude to set up the linkedin mcp server for me", "hand_off_coding", {}),
    ("install ffmpeg on this mac for me", "hand_off_coding", {}),
    ("help me set up this mcp server https://github.com/example/weather-mcp", "hand_off_coding", {}),
    ("open youtube and search for lofi music", "open_link", {}),
    ("set the brightness a little lower, like thirty", "set_brightness", {"level": 30}),
    ("can you make the screen a little less bright", "set_brightness", [{"change": "down"}, {"by": "-"}]),
    ("it's too loud", "set_volume", {}),
    ("press command shift t", "press_keys", {}),
    ("remember that my brother's name on whatsapp is John Doe", "remember", {}),
    ("where's the pdf my boss sent me last week on whatsapp", ("whatsapp_search", "whatsapp_find"), {}),
    ("is anything playing right now? pause it", "media", {"action": "pause"}),
    ("is my email connected?", "connections", {}),
    ("is the email MCP connected", "connections", {}),
    ("can you tell me whether my mail thing is hooked up to you", "connections", {}),
    ("which of my MCP servers are working", "connections", {}),
    ("do you have access to my linear account", "connections", {}),
    ("check my email", ("gmail__search_threads", "account_connector"), {}),
    ("draft an email to john saying I'll call him tonight", ("gmail__create_draft", "account_connector"), {}),
    ("I want you to search for the current price of PS5 in India.", "web_search", {"query": "ps5"}),
    ("what's the weather going to be like in springfield tomorrow", "weather", {"where": "springfield", "when": "tomorrow"}),
    ("will it rain this afternoon", "weather", {}),
    ("where am I right now", "location", {}),
    ("which city is this laptop in", "location", {}),
    ("who won the formula one race last weekend", "web_search", {}),
    ("look up how many calories are in a dosa", "web_search", {"query": "dosa"}),
    ("google the release date of GTA 6", "web_search", {"query": "gta"}),
    ("open flipkart and show me the ps5 listings", "open_link", {"where": "flipkart"}),
    ("how many files do i have in my downloads ?", "list_folder", {"folder": "download"}),
    ("what's in my desktop folder", "list_folder", {"folder": "desktop"}),
    ("what's jane doe's name on her whatsapp profile", "whatsapp_contact", {"name": "jane"}),
    ("can you show me jane doe's DP", "whatsapp_picture", {"name": "jane"}),
    ("how many days are left until christmas", "clock", {"until": "christmas"}),
    ("what's the last message i got on whatsapp", "whatsapp_read", {}),
    ("who messaged me last on whatsapp", "whatsapp_read", {}),
    ("how many whatsapp groups am i part of", "whatsapp_stats", {}),
    ("who is still waiting on my reply on whatsapp", "whatsapp_stats", {}),
    ("which whatsapp chat have i been most active in this week", "whatsapp_stats", {}),
    ("search all my whatsapp chats for the wifi password", ("whatsapp_find", "whatsapp_search"), {}),
    ("is it already past five in the evening", "clock", {}),
    ("remind me to call the dentist at four", "reminder", {"action": "set", "what": "dentist"}),
    ("remind me to drink water every hour", "reminder", {"action": "set", "when": "every hour"}),
    ("what reminders do I have", "reminder", {"action": "list"}),
    ("stop reminding me to drink water", "reminder", {"action": "forget", "what": "water"}),
    ("move the dentist reminder to six in the evening", "reminder", {"action": "change", "what": "dentist"}),
    ("download a picture of tyrion lannister", "find_images", {"query": "tyrion"}),
    ("download this https://example.com/files/report.pdf", "download", {"where": "example.com"}),
    ("what does my resume say about my last job", "read_file", {"what": "resume"}),
    ("delete the screenshot on my desktop called old notes", "move_to_trash", {"what": "old notes"}),
    ("bring back the file you just deleted", "restore_from_trash", {}),
    ("save that as a routine called morning brief", "routine", {"action": "save", "name": "morning brief"}),
    ("what routines have I saved", "routine", {"action": "list"}),
    ("what's on my clipboard", "clipboard", {}),
    ("from now on talk like a knight from game of thrones", "personality", {"style": "knight"}),
    ("stop the accent and talk normally again", "personality", {}),
    ("my brother is John Doe in my contacts, remember that", "remember", {"fact": "brother"}),
    ("tell my brother John Doe on whatsapp that I'm on my way", "whatsapp_send", {"relation": "brother"}),
    ("create a file on the desktop called test.txt and write some dialogue from game of thrones in it", "write_file", {"name": "test.txt"}),
    ("rewrite test.txt on my desktop so it only says hello", "write_file", {"how": "replace"}),
    ("what are all the apps that are open on my computer right now", "open_apps", {}),
    ("click the send button in mail", "use_app", {"action": "click", "target": "send"}),
    ("tick the remember me box on this page", "use_app", {"action": "click", "target": "remember"}),
    ("type hello world into the search box in spotify", "use_app", {"action": "type", "text": "hello world"}),
    # A CLICK ON A PATH LIKE "VIEW > AS LIST" IS SENT TO THE MENU, SO EITHER FORM DOES IT.
    ("in finder, choose view as list from the menu", "use_app", [{"action": "menu", "target": "list"}, {"action": "click", "target": "> as list"}]),
    ("scroll to the bottom of this window", "use_app", {"action": "scroll", "target": "bottom"}),
    ("summarise what was talked about today in the office group on whatsapp", "whatsapp_read",
     [{"chat": "office", "day": "today"}, {"chat": "office", "day": time.strftime("%Y-%m-%d")}]),
]

GMAIL = [
    ("gmail__search_threads", "From the gmail service: Search Gmail threads with a Gmail search query, newest first.",
     {"query": {"type": "string"}, "max_results": {"type": "integer"}}, []),
    ("gmail__get_thread", "From the gmail service: Get one Gmail thread and all its messages.", {"thread_id": {"type": "string"}}, ["thread_id"]),
    ("gmail__create_draft", "From the gmail service: Create a draft email for the person to review and send.",
     {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}, ["to", "body"]),
]

CANNED = {
    "whatsapp_unread": "2 unread messages in 1 chats:\nJohn Doe: 2 unread, last from John Doe: are you coming tomorrow?",
    "whatsapp_read": ("Chat with John Doe, newest last. Lines from John are John's own messages.\n"
                      "The newest message is John's own, not John Doe's.\nThe last message from John Doe: [Fri 23 Oct, 9:10 PM] John Doe: did you reach?\n\n"
                      "[Fri 23 Oct, 9:10 PM] John Doe: did you reach?\n[Fri 23 Oct, 9:12 PM] John: yes reached"),
    "whatsapp_find": "Best matches out of 812 messages:\n[Mon 2 Mar, 4:01 PM in John Doe] Me: Flat 12, Example Residency, Road no 1, Springfield 12345",
    "look_at_screen": "Front app: Google Chrome\nWindow: Lofi Girl - YouTube\nGoogle Chrome tab in front: Lofi Girl - YouTube — https://www.youtube.com/watch?v=jfKfPfyJRdk",
    "connections": "Internet: online\nModel: gpt-oss:20b\nWhatsApp: connected (linked as John)\nEmail through gmail (from Claude Code): connected (9 tools)\nMCP server linear (from Claude Code): needs sign-in (401 Unauthorized)\nMCP server freecad (from Claude Code): connected (14 tools)\nMCP server docs (from Codex): connected (4 tools)",
    "gmail__search_threads": "thread 18c2a (Sat 24 Oct, 2:10 PM) GitHub <noreply@github.com>: [open-slate] PR merged\nthread 18c1f (Fri 23 Oct) Jane Doe: Dinner on Sunday?",
    "gmail__create_draft": "Draft created: id r-551, to john@example.com.",
    "find_files": "/Users/johndoe/Desktop/projects/open-slate (changed 14 Oct 2026)\n/Users/johndoe/Documents/Resume 2026.pdf (changed 02 Sep 2026)",
    "open_file": "Opened /Users/johndoe/Documents/Resume 2026.pdf in Finder.",
    "hand_off_coding": "Opened Claude Code in a Terminal window in /Users/johndoe/Desktop/projects/open-slate with the task.",
    "account_connector": "You have 2 unread emails: GitHub says your open-slate pull request was merged, and Jane Doe asks about dinner on Sunday.",
    "whatsapp_search": "[Mon 19 Oct, 10:02 AM in Office] John Doe (boss): [document] (file Q3-plan.pdf)",
    "web_search": "1. Sony PlayStation5 Online in India at Best Prices - Flipkart — www.flipkart.com\n   The PS5 gaming console delivers eye-catching graphics with hardware that supports ray tracing.\n"
                  "2. Amazon.in: Ps5 — www.amazon.in\n   Discover a wide selection of PS5 games, consoles, and gaming accessories.\n"
                  "3. Sony PS5 Consoles | Reliance Digital — www.reliancedigital.in\n   Compare Slim, Digital, & Disc Models.\n\n"
                  "The snippets are short; read_result reads a whole page.",
    "find_images": "1. Tyrion Lannister Season 8 — 1920x1080, from wallpapercave.com\n2. Peter Dinklage as Tyrion — 800x1200, from wikipedia.org\n\nThe first ones are the best matches; download saves one by its number.",
    "weather": "Springfield, Illinois, United States, the next seven days:\nToday: clear, 23 to 32°C, 0% chance of rain\nMonday 26 Oct: partly cloudy, 22 to 31°C, 10% chance of rain",
    "location": "Springfield, Illinois, United States (39.8017, -89.6437), from Location Services, within 65 m.",
    "reminder": "Reminder set: call the dentist, 4 PM today.",
    "write_file": "Wrote /Users/johndoe/Desktop/test.txt and opened it.",
    "read_tab": "Why sleep matters — https://example.com/sleep\n\nSleep consolidates memory and clears waste from the backend. Adults need 7 to 9 hours.",
}


def claude_backend(model, picked):
    """Claude through the person's own login; anything outside Happy's tools is recorded and refused, never run."""
    from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

    from happy import paths
    from happy.agent.claude import Claude

    (paths.HOME / "claude-session.json").unlink(missing_ok=True)
    # THE APP HANDS CLAUDE WHATSAPP THROUGH ITS MCP SERVER; HERE HAPPY'S OWN MOCKED WHATSAPP TOOLS STAND IN FOR IT.
    for registered in tools.REGISTRY.values():
        if registered.name.startswith("whatsapp_"):
            registered.local_only = False
    cfg = Config()
    cfg.set("brain.model", model)
    backend = Claude(cfg)

    async def refuse(name, args, context):
        if name.startswith("mcp__happy__"):
            return PermissionResultAllow()
        # A CONNECTOR LIKE mcp__claude_ai_Gmail__search_threads SCORES AS THE MOCKED gmail__search_threads.
        parts = name.split("__")
        picked.append((f"gmail__{parts[-1]}" if "gmail" in name.lower() else name, args))
        return PermissionResultDeny(message="Not available in this test.")

    backend.permit = refuse
    return backend


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
    if base_url == "claude":
        backend = claude_backend(model, picked)
    else:
        from happy.agent import openai_compatible

        openai_compatible.tools.call = fake
        backend = openai_compatible.OpenAICompatible(Config(), base_url, model)
    await backend.start()
    score, rows = 0, []
    only = os.environ.get("ONLY", "").lower()
    for text, want, want_args in [c for c in CASES if any(o in c[0].lower() for o in only.split("|"))] if only else CASES:
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
        # A LIST OF ARGUMENTS IS THE SAME INSTRUCTION WRITTEN DIFFERENT WAYS, LIKE "DOWN" OR A NEGATIVE STEP.
        options = want_args if isinstance(want_args, list) else [want_args]
        hits = [c for c in picked if c[0] in wanted and any(all(str(v).lower() in json.dumps(c[1]).lower() for v in o.values()) for o in options)]
        right = bool(hits)
        chosen = hits[0] if hits else (picked[0] if picked else (None, {}))
        score += right
        trail = " → ".join(c[0] for c in picked)
        rows.append(f"{'✓' if right else '✗'} {took:5.1f}s first {first or 0:4.1f}s  {text!r} -> {trail} {json.dumps(chosen[1])[:80]} | said: {''.join(spoken)[:90]!r}")
        print(rows[-1], flush=True)
    print(f"\n{model}: {score}/{len(rows)}")


# `python evals/choice.py claude sonnet` scores Claude through the Claude Code login instead of a local model.
if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:11434/v1",
                     sys.argv[2] if len(sys.argv) > 2 else "gpt-oss:20b"))
