"""Scores whether a page opened on request is the one asked for, when the first result is a near miss only its page gives away."""

import asyncio
import json
import os
import re
import sys
import time

os.environ.setdefault("HAPPY_HOME", "/tmp/happy-bench")

from happy import tools
from happy.agent import Problem, Text
from happy.config import Config


def video(code, title, words, listed="", snippet=""):
    return {"href": f"https://www.youtube.com/watch?v={code}", "page": title, "listed": listed, "snippet": snippet,
            "html": f"<html><head><title>{title} - YouTube</title></head><body><h1>{title}</h1>"
                    f"<p>{words} Official lyrical video, streaming now. Like, share and subscribe for more songs from the album. "
                    f"Music label channel. Comments are turned off for this video. About Press Copyright Contact us Creators.</p></body></html>"}


# GOOGLE LISTED THE VEERA VEERA VERSIONS UNDER ONE CAST LINE; ONLY THE PAGE SAID WHICH LANGUAGE IT WAS.
VEERA = ("OM | Dhanush | Mammootty | Sai Pallavi | Rajkumar - YouTube", [
    video("yfHDJWWm0LE", "Veera Veera Lyrical (Telugu) | OM | Dhanush | Mammootty | Sai Pallavi", "Veera Veera, Telugu lyrics."),
    video("Kd82LmQx0Tw", "Veezha Veera Lyrical (Tamil) | OM | Dhanush | Mammootty | Sai Pallavi", "Veezha Veera, Tamil lyrics."),
    video("p3NcV0rTq8A", "Veera Veera Lyrical (Hindi) | OM | Dhanush | Mammootty | Sai Pallavi", "Veera Veera, Hindi lyrics."),
])
# AS GOOGLE REALLY LISTED THEM ON 2026-10-27: ITS OWN TITLES, ONE OF THEM DROPPING THE PART THAT SAID WHICH LANGUAGE IT WAS.
VEERA_LIVE = ("", [
    video("yfHDJWWm0LE", "Veera Veera Lyrical (Telugu) | OM | Dhanush | Mammootty | Sai Pallavi | Rajkumar | Sai Abhyankkar", "Veera Veera, Telugu lyrics.",
          "OM | Dhanush | Mammootty | Sai Pallavi | Rajkumar", "YouTube · Divo Music 3:59 Veera Veera – the electrifying Telugu single from OM Chapter 1."),
    video("Kd82LmQx0Tw", "Veezha Veera Lyrical (Tamil) | OM | Dhanush | Mammootty | Sai Pallavi | Rajkumar | Sai Abhyankkar", "Veezha Veera, Tamil lyrics.",
          "Veezha Veera Lyrical (Tamil) | OM | Dhanush | Mammootty", "YouTube · Saregama Tamil 3:28 Veezha Veera from OM Chapter 1: Udhiram."),
    video("p3NcV0rTq8A", "Veera Veera Lyrical (Hindi) | OM | Dhanush | Mammootty | Sai Pallavi | Rajkumar | Sai Abhyankkar", "Veera Veera, Hindi lyrics.",
          "VeeraVeera", "YouTube Veera Veera Lyrical (Hindi) | OM | Dhanush | Mammootty"),
])
KANTARA = ("Kantara Chapter 1 | Official Trailer | Rishab Shetty | Hombale Films - YouTube", [
    video("Gx81NcPq2Lk", "Kantara Chapter 1 Official Trailer (Kannada) | Rishab Shetty", "Kantara Chapter 1, the Kannada trailer."),
    video("Hm42TbVw9Zs", "Kantara Chapter 1 Official Trailer (Hindi) | Rishab Shetty", "Kantara Chapter 1, the Hindi trailer."),
])
def shop(href, title, listed, snippet, words):
    host = href.split("/")[2].removeprefix("www.")
    return {"href": href, "page": title, "listed": listed, "snippet": snippet, "host": host, "site": host.split(".")[0],
            "html": f"<html><head><title>{title}</title></head><body><h1>{title}</h1>"
                    f"<p>{words} Free delivery by tomorrow. 7 days replacement policy. Bank offers and no cost EMI available on select cards. "
                    f"Ratings and reviews. Specifications: 1 console, 1 DualSense wireless controller, HDMI cable, AC power cord.</p></body></html>"}


# THE RESULTS OF 2026-10-27, WHEN IT READ THE FLIPKART PAGE AS RESULT 2 OF ONE SEARCH AND THEN OPENED RESULT 2 OF A LATER AMAZON ONE.
PS5 = ("", [
    shop("https://www.amazon.in/Sony-PlayStation5-Gaming-Console-Slim/dp/B0GNMKL3VP",
         "Sony PlayStation5 Gaming Console (Slim) | Disc Edition - 1TB : Amazon.in: Video Games",
         "Sony PlayStation5 Gaming Console (Slim) | Disc Edition - 1TB", "Amazon.in · ₹69,985.00 · In stock", "Price: ₹69,985.00 Disc Edition 1TB."),
    shop("https://www.flipkart.com/sony-ps5-console-digital-fortnite-bundle-slim-1-tb-yes/p/itm1660d204e39f8",
         "SONY PS5 Console Digital - Fortnite Bundle (Slim) 1 TB with Yes Price in India - Buy SONY PS5 Console Digital - Fortnite Bundle (Slim) 1 TB with Yes White Online - SONY : Flipkart.com",
         "SONY PS5 Console Digital - Fortnite Bundle (Slim) 1 TB with Yes", "Flipkart · ₹44,990 · ₹42,740 with bank offers",
         "₹44,990 Digital Edition 1 TB with a Fortnite bundle code."),
    shop("https://www.amazon.in/stores/PlayStation/page/5D2B6F4E", "Amazon.in: Sony India: PS5 Console", "Amazon.in: Sony India: PS5 Console",
         "Shop PS5 consoles, controllers and games from the official store on Amazon.in.", "PS5 Console, PS5 Digital Edition, PS5 Pro. Shop the store."),
    shop("https://www.amazon.in/Sony-PlayStation-Digital-Edition-Slim/dp/B0CY5QW186",
         "Sony PlayStation 5 Digital Edition (Slim) : Amazon.in: Video Games", "Sony PlayStation 5 Digital Edition (Slim)",
         "Amazon.in · ₹64,990.00 · 825GB SSD", "Price: ₹64,990.00 Digital Edition 825GB."),
    shop("https://www.flipkart.com/sony-playstation5-digital-edition-slim-1-tb/p/itm6a1c0e5b2f7d1",
         "SONY Playstation5 Digital Edition (Slim) 1 TB Price in India - Buy SONY Playstation5 Digital Edition (Slim) 1 TB White Online - SONY : Flipkart.com",
         "SONY Playstation5 Digital Edition (Slim) 1 TB", "Flipkart · ₹54,990 · Out of stock", "₹54,990 Digital Edition 1 TB. Currently unavailable."),
    shop("https://www.smartprix.com/gaming-consoles/sony-playstation-5-digital-slim-1tb-ppd1y2ohqk7b",
         "Sony PlayStation 5 Digital Slim 1TB Best Price in India 2026 - Smartprix", "Sony PlayStation 5 Digital Slim 1TB Best Price in India",
         "Lowest price ₹44,990 at Flipkart. Compare prices from Amazon, Flipkart, Croma and Reliance Digital.",
         "Lowest price ₹44,990 at Flipkart. Amazon ₹64,990. Croma ₹49,990. Reliance Digital ₹49,990."),
    dict(shop("https://www.croma.com/sony-playstation-5-slim-digital-console-1tb/p/304523", "Sony PlayStation 5 Slim Digital Console (1TB) - Croma",
              "Sony PlayStation 5 Slim Digital Console (1TB)", "Croma · ₹49,990 · Free delivery", ""), html=None),
])
AMAZON_DISC, FLIPKART_FORTNITE, AMAZON_STORE, AMAZON_DIGITAL, FLIPKART_DIGITAL, SMARTPRIX, CROMA = (p["href"] for p in PS5[1])
# THE ORDER EACH OF THAT TURN'S SEARCHES CAME BACK IN, AS FAR AS THE LOG SHOWS IT; ANY OTHER QUERY IS RANKED BY ITS WORDS.
ORDERS = {
    "PS5 digital 1TB price Amazon Flipkart": [AMAZON_DISC, FLIPKART_FORTNITE, FLIPKART_DIGITAL, AMAZON_DIGITAL, SMARTPRIX, AMAZON_STORE],
    "PS5 digital 1TB Flipkart price": [FLIPKART_DIGITAL, FLIPKART_FORTNITE, SMARTPRIX, AMAZON_DIGITAL, AMAZON_DISC],
    "PS5 digital 1TB price best buy india": [SMARTPRIX, FLIPKART_FORTNITE, CROMA, FLIPKART_DIGITAL, AMAZON_DIGITAL],
    "PS5 digital 1TB price Amazon India": [AMAZON_DIGITAL, AMAZON_STORE, AMAZON_DISC, FLIPKART_FORTNITE, SMARTPRIX],
}
# THAT TURN AS IT WENT, WITH EACH READ GIVEN BY ITS PLACE IN THE LIST, SINCE THE NUMBER THERE DEPENDS ON HOW SEARCHES ARE NUMBERED.
PS5_ASKED = ("Can you search for the prices of PS5 on both Amazon, Flipkart and any other provider on the internet and give me which places PS5 "
             "for the least price? And specifically, I want the PS5, the digital version that is 1 TB.",
             [("web_search", "PS5 digital 1TB price Amazon Flipkart"), ("read_result", 1),
              ("web_search", "PS5 digital 1TB Flipkart price"), ("read_result", 2),
              ("web_search", "PS5 digital 1TB price best buy india"), ("read_result", 3),
              ("web_search", "PS5 digital 1TB price Amazon India"), ("read_result", 1)],
             "The cheapest place for a 1 TB PS5 Digital Edition is Flipkart, where the Fortnite Bundle is listed at ₹44,990 (₹42,740 with bank offers). "
             "Amazon sells the digital model for ₹64,990 and the disc edition for ₹69,985. Thus Flipkart offers the lowest price.")
PUSHPA = ("Pushpa 2 The Rule | Sooseki Song | Allu Arjun | Rashmika - YouTube", [
    video("Rt5Bq0LmYa3", "Sooseki Full Video Song (Telugu) | Pushpa 2 The Rule", "Sooseki, the Telugu video song."),
    video("Wn7Ce2KpXo9", "Angaaron Full Video Song (Hindi) | Pushpa 2 The Rule", "Angaaron, the Hindi video song."),
    video("Zq1Dv8HsUe4", "Kandaaru (Sooseki) Full Video Song (Malayalam) | Pushpa 2 The Rule", "Kandaaru, the Malayalam video song."),
])

# (WHAT THEY SAY, TURN BY TURN), THE RESULTS EVERY SEARCH RETURNS, AND THE INDEX OF THE ONE THEY WANT.
CASES = [
    (["how many likes does the Veera Veera video from Om have",
      "can you open the Tamil lyric video on YouTube and show it to me? I want the Tamil version"], VEERA, 1),
    (["open the tamil lyric video of Veera Veera from Om on youtube"], VEERA, 1),
    (["play the hindi trailer of Kantara chapter 1 on youtube"], KANTARA, 1),
    (["what's the Kantara chapter 1 trailer like", "open the hindi one for me"], KANTARA, 1),
    (["put on the malayalam version of the Sooseki song from Pushpa 2"], PUSHPA, 2),
    (["open the telugu lyric video of Veera Veera from Om"], VEERA, 0),
    (["how many likes does the Veera Veera video from Om have",
      "can you open the Tamil lyric video on YouTube and show it to me? I want the Tamil version"], VEERA_LIVE, 1),
    (["open the veera veera song from om in tamil"], VEERA_LIVE, 1),
    ([PS5_ASKED, "I don't understand how Flipkart sells the entire digital PS5 for just 4490. It doesn't make sense and it is too different from what Amazon offers, right? "
      "Can you just uh see or show me up the uh Fortnite, I mean the Flipkart PS5 page?"], PS5, 1),
]


class Page:
    def __init__(self, url, html):
        self.url, self.text, self.status_code = url, html, 200


async def main(base_url, model):
    import curl_cffi.requests

    from happy.system import macos
    from happy.tools import apps, web

    tools.load()
    for registered in tools.REGISTRY.values():
        registered.needs = None
    current = {"listing": "", "videos": []}
    opened = []
    # GOOGLE, THE FETCH AND THE BROWSER ARE STUBBED; WEB_SEARCH, READ_RESULT AND OPEN_LINK RUN AS THEY ARE.
    def google(query):
        # GOOGLE PUTS THE VERSION A QUERY NAMES FIRST, SO SEARCHING AGAIN WITH "TAMIL" IN IT IS A WAY TO THE RIGHT ONE.
        words = set(query.lower().split())
        # A SHOP'S NAME IN THE QUERY PUTS ITS PAGES FIRST, SO EACH SEARCH NUMBERS THE SAME PAGES DIFFERENTLY.
        ranked = sorted(current["videos"], key=lambda v: -len(words & set(f"{v['page']} {v.get('site', '')}".lower().replace("(", " ").replace(")", " ").split())))
        if query in ORDERS:
            ranked = [v for href in ORDERS[query] for v in current["videos"] if v["href"] == href]
        return "", [{"title": v["listed"] or current["listing"], "href": v["href"], "host": v.get("host", "youtube.com"), "body": v["snippet"]} for v in ranked]

    web.google = google
    from curl_cffi.requests.exceptions import RequestException

    def get(url, **kwargs):
        page = {v["href"]: v["html"] for v in current["videos"]}.get(url, "<html></html>")
        # ONE RESULT OF THAT TURN COULD NOT BE REACHED AT ALL.
        if page is None:
            raise RequestException("Failed to perform, curl: (92) HTTP/2 stream 1 reset by server")
        return Page(url, page)

    curl_cffi.requests.get = get
    macos.open_path = lambda path, app=None, reveal=False: opened.append(path)
    apps.webbrowser.open = opened.append
    real = tools.call
    trail = []

    async def call(name, args):
        trail.append((name, dict(args)))
        # BEFORE=1 NUMBERS EVERY SEARCH FROM 1 AGAIN, FOR THE PRE-FIX SCORE ON THE SAME MOCKS.
        if name == "web_search" and os.environ.get("BEFORE"):
            web.results.clear()
        if name in ("web_search", "read_result", "open_link"):
            return await real(name, args)
        return "Done."

    tools.call = call
    from happy.agent import openai_compatible

    openai_compatible.tools.call = call
    backend = openai_compatible.OpenAICompatible(Config(), base_url, model)
    await backend.start()

    async def replay(text, steps, answer, emit):
        """A turn as it really went, through the real tools and the real repeat check, so the next turn starts from the history it had."""
        tools.asked.set(text)
        tools.seen.set([])
        backend.history.append({"role": "user", "content": openai_compatible.stamped(text)})
        backend.done_calls, backend.last, listing = {}, time.time(), ""
        for i, (name, value) in enumerate(steps):
            if name == "read_result":
                value = int(re.findall(r"^(\d+)\. ", listing, re.M)[value - 1])
            args = {"query": value} if name == "web_search" else {"number": value}
            call = {"id": f"replay_{i}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}
            backend.history.append({"role": "assistant", "content": "", "tool_calls": [call]})
            await backend.run(call, emit)
            if name == "web_search":
                listing = backend.history[-1]["content"]
        backend.history.append({"role": "assistant", "content": answer})

    right = clean = 0
    only = os.environ.get("ONLY", "").lower()
    cases = [c for c in CASES if only in " ".join(t[0] if isinstance(t, tuple) else t for t in c[0]).lower()]
    for turns, (listing, videos), want in cases:
        current.update(listing=listing, videos=videos)
        web.results, web.last_read = [], ""
        trail.clear()
        opened.clear()
        await backend.reset()
        started, spoken = time.monotonic(), []

        def emit(event):
            if isinstance(event, Text):
                spoken.append(event.delta)
            if isinstance(event, Problem):
                spoken.append(f"[problem: {event.message}]")

        for text in turns:
            spoken.clear()
            await (replay(*text, emit) if isinstance(text, tuple) else backend.turn(text, emit))
        wanted = videos[want]["href"]
        got = wanted in opened
        # A SEARCH PAGE ON THE WAY IS A SPARE TAB, NOT A WRONG ONE; ONLY ANOTHER VERSION COUNTS AGAINST IT.
        wrong = [o for o in opened if o != wanted and o in {v["href"] for v in videos}]
        right += got
        clean += got and not wrong
        names = {v["href"]: v["page"].split("|")[0].strip() for v in videos}
        steps = " → ".join(f"{n}({a.get('where') or a.get('query') or a.get('number') or ''})" for n, a in trail)
        print(f"{'✓' if got and not wrong else '~' if got else '✗'} {time.monotonic() - started:5.1f}s {turns[-1]!r}\n    {steps if len(steps) <= 260 else '…' + steps[-260:]}\n"
              f"    opened: {[names.get(o, o) for o in opened]}\n    said: {''.join(spoken)[:140]!r}", flush=True)
    print(f"\n{model}: {right}/{len(cases)} opened the one asked for, {clean}/{len(cases)} without opening a wrong one first")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:11434/v1",
                     sys.argv[2] if len(sys.argv) > 2 else "gpt-oss:20b"))
