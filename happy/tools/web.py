"""Searching the web and reading what comes back, without opening anything on screen."""

import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Annotated

import httpx

from happy import paths
from happy.tools import tool
from happy.tools.browser import text_of

# EACH ENGINE MISSES SOME QUERIES AND DDGS'S "AUTO" ASKS A RANDOM FEW, SO THEY ARE ASKED ONE AT A TIME UNTIL ONE ANSWERS.
ENGINES = ("bing", "yahoo", "duckduckgo", "brave", "mojeek")
CHROMES = {
    "darwin": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"],
    "win32": [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"],
}.get(sys.platform, ["/usr/bin/google-chrome", "/usr/bin/chromium"])
AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
one_chrome = threading.Lock()
LONGEST = 6000
results = []
searched_at = 0.0
last_read = ""


def google(query):
    """Google's answer and results, from a Chrome nobody sees, since Google shows nothing to a client without JavaScript."""
    chrome = next((path for path in CHROMES if Path(path).exists()), None)
    if not chrome:
        return "", []
    url = str(httpx.URL("https://www.google.com/search", params={"q": query, "hl": "en"}))
    with one_chrome:
        try:
            page = subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                                   f"--user-data-dir={paths.HOME / 'search-chrome'}", f"--user-agent={AGENT}",
                                   "--virtual-time-budget=5000", "--dump-dom", url],
                                  capture_output=True, text=True, timeout=25).stdout
        except (OSError, subprocess.TimeoutExpired):
            return "", []
    return google_page(page) if page else ("", [])


def google_page(page):
    """The AI overview and the numbered results on a Google results page."""
    import lxml.html

    doc = lxml.html.fromstring(page)
    for hidden in doc.xpath("//script|//style"):
        hidden.drop_tree()
    overview, found = "", []
    for heading in doc.xpath("//h3"):
        title = " ".join(heading.text_content().split())
        link = heading.xpath("ancestor::a[@href][1]")
        if not link:
            if not overview and "AI" in title:
                overview = " ".join(" ".join(heading.getparent().itertext()).split())[len(title):]
                # WHAT FOLLOWS THE ANSWER IS GOOGLE'S OWN BUTTONS AND SOURCE CARDS, READ OUT AS IF THEY WERE THE ANSWER.
                overview = re.split(r"\s(?:Shared\s*\d+\s*files|Show all|AI responses may include mistakes)", overview)[0]
            continue
        href = link[0].get("href")
        # GOOGLE'S OWN /goto ADDRESS LEADS TO THE PAGE WHEN FETCHED; THE REAL ONE IS NOWHERE ON THE PAGE.
        href = "https://www.google.com" + href if href.startswith("/") else href
        block, body, host = link[0], "", ""
        while block.getparent() is not None and not body:
            block = block.getparent()
            words = " ".join(block.text_content().split()).replace(title, " ", 1)
            for cite in block.xpath(".//cite"):
                said = " ".join(cite.text_content().split())
                host = host or said.split("›")[0].strip().removeprefix("https://").removeprefix("www.")
                words = words.replace(said, " ")
            words = " ".join(words.split()).strip(" ·")
            if len(words) > 60:
                body = words[:300]
        found.append({"title": title, "href": href, "host": host, "body": body})
    return overview[:1500], found


@tool(say="Searching.", label="Searching for {query}")
def web_search(query: Annotated[str, "what to look up, in a few words"]):
    """Search the web to find out something: prices, news, facts, how-tos, anything not on this computer. Gives numbered results; read one with read_result."""
    from ddgs import DDGS
    from ddgs.exceptions import DDGSException

    global searched_at
    searched_at = time.monotonic()
    overview, found = google(query)
    for engine in ENGINES if not found else ():
        try:
            found = [r for r in DDGS(timeout=8).text(query, max_results=8, backend=engine) if r.get("href")]
        except DDGSException:
            continue
        if found:
            break
    if not found:
        return f"No search engine found anything for {query}. Try fewer or plainer words."
    tell_apart(found)
    for older in results:
        older.pop("fetched", None)
    # NUMBERS CARRY ON FROM THE LAST SEARCH; "2" HAD MEANT THE FLIPKART PAGE IT READ, AND A LATER SEARCH HANDED "2" TO AN AMAZON ONE.
    first = len(results) + 1
    results.extend(found)
    lines = [f"{i}. {r.get('title', '')} — {r.get('host') or httpx.URL(r['href']).host}\n   {r.get('body', '')}" for i, r in enumerate(found, first)]
    answer = f"Google's AI overview: {overview}\n\n" if overview else ""
    return answer + "\n".join(lines) + "\n\nThe snippets are short; read_result reads a whole page."


def own_title(page):
    """The title a page gives itself, which a result's listed title can leave out, like which language a video is in."""
    import html

    found = re.search(r"<title[^>]*>(.*?)</title>", page or "", re.S | re.I)
    return " ".join(html.unescape(found.group(1)).split()).removesuffix(" - YouTube") if found else ""


def tell_apart(found):
    """Each result renamed by its page's own title where that says more than Google's, like which language a video is in or a 1TB console."""
    from concurrent.futures import ThreadPoolExecutor

    from curl_cffi import requests
    from curl_cffi.requests.exceptions import RequestException

    def key(result):
        return re.sub(r"\s*(?:\.\.\.|…)\s*$", "", result.get("title", "")).removesuffix(" - YouTube")

    def fetched(result):
        try:
            return requests.get(result["href"], impersonate="safari", timeout=4)
        except RequestException:
            return None

    names = [key(r) for r in found]
    with ThreadPoolExecutor(max(len(found), 1)) as pool:
        pages = list(pool.map(fetched, found))
    for result, name, page in zip(found, names, pages):
        if page is None:
            continue
        # KEPT, SO READING A RESULT RIGHT AFTER THE SEARCH DOES NOT FETCH IT AGAIN.
        result["fetched"] = page
        title, listed = own_title(page.text), words_of(name)
        # A TITLE HOLDING ALL OF GOOGLE'S AND MORE, LIKE "DISC EDITION - 1TB", SAYS MORE, AS DOES ANY REAL ONE WHEN RESULTS SHARE A TITLE; "REDDIT" SAYS LESS.
        if title and (listed < words_of(title) or names.count(name) > 1 and listed & words_of(title)):
            result["title"] = title


def words_of(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def listed(text):
    """The search result whose title and site hold every word of the text, when a result is named instead of numbered."""
    named = words_of(text)
    return next((r for r in reversed(results) if len(named) >= 2 and named <= words_of(f"{r.get('title', '')} {r.get('host', '')}")), None)


def version_asked(url, said):
    """The search result their words name, when the one about to open is another version of it, like the Kannada trailer when they said Hindi."""
    picked = next((r for r in results if url in (r.get("href"), r.get("address"))), None)
    if picked is None or not said:
        return None
    asked, mine = words_of(said), words_of(picked.get("title", ""))
    fit = lambda result: len(asked & words_of(result.get("title", "")))
    # ONLY A NEAR TWIN COUNTS, SO A TITLE THAT MERELY SHARES MORE OF THEIR WORDS, LIKE "OPEN IN THE YOUTUBE APP", NEVER TAKES OVER.
    twins = [r for r in results if r is not picked and len(mine & words_of(r.get("title", ""))) * 2 >= len(mine | words_of(r.get("title", "")))]
    best = max(twins, key=fit, default=None)
    return best if best and fit(best) > fit(picked) else None


PRICES = [r'priceToPay[^>]*class="aok-offscreen">\s*([^<]+?)\s*</span>',
          # FLIPKART KEEPS ITS PRICE ONLY IN THE PAGE'S DATA, SO A ₹44,990 PS5 WAS QUOTED FROM GOOGLE'S OVERVIEW AND DOUBTED.
          r'"finalPrice"\s*:\s*([\d.]+)',
          r'"@type"\s*:\s*"Offer".{0,300}?"price"\s*:\s*"?([\d.,]+)',
          r'itemprop="price"[^>]*content="([\d.,]+)"',
          r'property="(?:og|product):price:amount"[^>]*content="([\d.,]+)"']


def stated_price(page):
    """The price a shop's page gives for itself, which text extraction drops along with the buy box."""
    for pattern in PRICES:
        found = re.search(pattern, page, re.S)
        if found:
            return found.group(1)
    return ""


@tool(say="Reading that page.", label="Reading result {number}")
def read_result(number: Annotated[int, "the result's number from web_search"]):
    """Read one page from the last web_search, by its number, when the snippets do not hold the answer."""
    import trafilatura
    from curl_cffi import requests
    from curl_cffi.requests.exceptions import RequestException

    if not results:
        return "There are no search results yet; call web_search first."
    if not 1 <= number <= len(results):
        return f"There are only {len(results)} results; pick one from 1 to {len(results)}."
    url = results[number - 1]["href"]
    # SHOPS TURN AWAY A PLAIN CLIENT; AMAZON LETS SAFARI'S LOOK THROUGH AND BLOCKS CHROME'S, SO SAFARI GOES FIRST.
    for browser in ("safari", "chrome"):
        try:
            page = results[number - 1].pop("fetched", None) or requests.get(url, impersonate=browser, timeout=15)
        except RequestException as error:
            page, failure = None, error
            continue
        text = trafilatura.extract(page.text, include_tables=True, favor_recall=True) or ""
        if len(text) < 200:
            text = text_of(page.text)
        if page.status_code < 400 and len(text) >= 200 and "captcha" not in page.text[:20000].lower():
            break
    if page is None:
        return f"Could not reach {url}: {failure}. Try another result."
    if page.status_code >= 400 or len(text) < 200:
        return f"Could not read {url}: the site sent no readable text (status {page.status_code}). Try another result."
    global last_read
    url = str(page.url)
    last_read = url
    # GOOGLE LISTED THE TELUGU AND TAMIL VIDEOS UNDER ONE CAST LINE; ONLY THE PAGE'S OWN TITLE SAID WHICH ONE IT WAS.
    title = own_title(page.text) or results[number - 1].get("title", "")
    results[number - 1].update(address=url, title=title)
    price = stated_price(page.text)
    heading = f"{title} — {url}" + (f"\nThe page's own price: {price}" if price else "")
    return f"{heading}\n\n{text[:LONGEST]}"
