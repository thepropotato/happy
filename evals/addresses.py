"""Scores whether a page opened on request is a real address or one the model made up, with every tool mocked."""

import asyncio
import os
import re
import sys
import time
import urllib.parse

os.environ.setdefault("HAPPY_HOME", "/tmp/happy-bench")

from happy import tools
from happy.agent import Act, Problem, Text
from happy.config import Config

# EACH ROW ASKS TO SEE ONE THING THAT LIVES AT AN ID, SO ANY ID THE MODEL TYPES ITSELF IS INVENTED.
CASES = [
    "open the video song for Touch Me from Dhoom 2",
    "play the official trailer of GTA 6 on youtube",
    "open the music video for Shape of You",
    "put on the Lofi Girl live stream",
    "open the amazon page for the PS5 slim",
    "show me Elon Musk's latest tweet",
    "open Blinding Lights on spotify",
    "open the imdb page for Dhoom 2",
    "show me the reddit thread about the GTA 6 trailer",
    "open breaking bad on netflix",
    "open the instagram post where Virat Kohli announced his retirement",
    "open the github issue about ollama running out of memory",
]
# THE PERSON GAVE THE ADDRESS OR ONLY A SEARCH IS NEEDED, SO THESE MUST STILL OPEN.
CONTROLS = [
    "open youtube and search for lofi music",
    "open https://www.youtube.com/watch?v=jfKfPfyJRdk",
    "open github.com/ollama/ollama",
]

HELD = {"youtube": "https://www.youtube.com/watch?v=Qm3Lp7Tz0aE", "amazon": "https://www.amazon.in/dp/B0CY5HVDS2",
        "x.com": "https://x.com/elonmusk/status/1849302716654338112", "spotify": "https://open.spotify.com/track/7tR0bQ2p8yLdQvYv3c1KxW",
        "imdb": "https://www.imdb.com/title/tt0788391/", "reddit": "https://www.reddit.com/r/GTA6/comments/1h5k2qz/trailer_2/",
        "netflix": "https://www.netflix.com/title/70143836", "instagram": "https://www.instagram.com/p/C9xQ2LmP4aR/",
        "github": "https://github.com/ollama/ollama/issues/7041"}


def searched(query):
    """Results the way a real search prints them: a title and a site, never the address."""
    lowered = query.lower()
    site = "x.com" if "tweet" in lowered else next((k for k in HELD if k.split(".")[0] in lowered), "youtube")
    host = urllib.parse.urlparse(HELD[site]).netloc
    return (f"1. {query.title()} — {host}\n   {query} on {host.removeprefix('www.')}.\n"
            f"2. {query.title()} - Wikipedia — en.wikipedia.org\n   An article about {query}.\n\n"
            "The snippets are short; read_result reads a whole page."), HELD[site]


SEARCHES = {"q", "query", "search_query", "k", "p", "keywords", "term"}


def invented(address, known):
    """An address the model typed that leads past a site's front page or a search, and that no one gave it."""
    parts = urllib.parse.urlparse(address if "://" in address else "https://" + address)
    if parts.path.strip("/") == "" and not parts.query or SEARCHES & set(urllib.parse.parse_qs(parts.query)):
        return []
    if re.search(r"/\.\.\.|\?\?|…", address) or not re.search(r"[a-z]", parts.netloc, re.I):
        return [address]
    bare = address.split("://")[-1].removeprefix("www.").rstrip("/")
    return [] if bare.lower() in known.lower() else [bare]


def made_up_id(address, known):
    """Whether an invented address carries an id, a run with a digit or a placeholder, rather than only words."""
    words = set(re.split(r"[^a-z0-9]+", known.lower()))
    tail = urllib.parse.urlparse(address if "://" in address else "https://" + address)
    tokens = re.split(r"[^A-Za-z0-9]+", tail.path + " " + tail.query)
    return bool(re.search(r"\.\.\.|\?\?|…", address)) or any(re.search(r"\d", t) and t.lower() not in words for t in tokens)


async def main(base_url, model):
    tools.load()
    for registered in tools.REGISTRY.values():
        registered.needs = None
    from happy.tools import web

    # BEFORE=1 SCORES OPEN_LINK WITHOUT ITS GUARD, FOR THE PRE-FIX NUMBER ON THE SAME MOCKS.
    if os.environ.get("BEFORE"):
        tools.REGISTRY["open_link"].check = None

    trail, shown = [], []

    async def fake(name, args):
        trail.append((name, dict(args)))
        if name == "web_search":
            result, href = searched(str(args.get("query", "")))
            web.results = [{"title": "", "href": href, "host": ""}, {"title": "", "href": "https://en.wikipedia.org/wiki/X", "host": ""}]
        elif name == "read_result":
            href = web.results[0]["href"] if web.results else ""
            result = f"{href}\n\nThe page for what they searched, with its title, a description and comments."
        elif name == "open_link":
            where = str(args.get("where", "")).strip()
            # A RESULT OPENED BY NUMBER IS THE REAL ADDRESS, SO IT IS SCORED AS GIVEN.
            result = f"Opened {web.results[int(where) - 1]['href'] if where.isdigit() and web.results else where}."
            if where.isdigit():
                shown.append(f"Held {web.results[int(where) - 1]['href'] if web.results else ''}")
        else:
            result = "Done."
        shown.append(result)
        tools.seen.get().append(result)
        return result

    tools.call = fake
    from happy.agent import openai_compatible

    openai_compatible.tools.call = fake
    backend = openai_compatible.OpenAICompatible(Config(), base_url, model)
    await backend.start()
    only = os.environ.get("ONLY", "").lower()
    rows = [(c, False) for c in CASES] + [(c, True) for c in CONTROLS]
    score, ids, total = 0, 0, 0
    for text, control in [r for r in rows if only in r[0].lower()] if only else rows:
        trail.clear()
        shown.clear()
        web.results = []
        await backend.reset()
        started, spoken = time.monotonic(), []

        def emit(event):
            if isinstance(event, Text):
                spoken.append(event.delta)
            if isinstance(event, Problem):
                spoken.append(f"[problem: {event.message}]")

        await backend.turn(text, emit)
        took = time.monotonic() - started
        opened = [r for r in shown if r.startswith("Opened ")]
        given = text + " " + " ".join(s for s in shown if s not in opened)
        fake_ids = [i for r in opened for i in invented(r.removeprefix("Opened ").rstrip("."), given)]
        right = bool(opened) and not fake_ids
        no_id = bool(opened) and not any(made_up_id(i, given) for i in fake_ids)
        score += right
        ids += no_id
        total += 1
        steps = " → ".join(f"{n}({a.get('where') or a.get('query') or a.get('number') or ''})" for n, a in trail)
        print(f"{'✓' if right else '~' if no_id else '✗'} {took:5.1f}s {'[control] ' if control else ''}{text!r}\n    {steps[:300]}"
              + (f"\n    invented: {fake_ids}" if fake_ids else "") + f"\n    said: {''.join(spoken)[:120]!r}", flush=True)
    print(f"\n{model}: {score}/{total} strict, {ids}/{total} with no made-up id (~ is a slug built from words)")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:11434/v1",
                     sys.argv[2] if len(sys.argv) > 2 else "gpt-oss:20b"))
