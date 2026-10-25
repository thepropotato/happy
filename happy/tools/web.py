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

    global results, searched_at
    results = []
    searched_at = time.monotonic()
    overview, results = google(query)
    for engine in ENGINES if not results else ():
        try:
            results = [r for r in DDGS(timeout=8).text(query, max_results=8, backend=engine) if r.get("href")]
        except DDGSException:
            continue
        if results:
            break
    if not results:
        return f"No search engine found anything for {query}. Try fewer or plainer words."
    lines = [f"{i}. {r.get('title', '')} — {r.get('host') or httpx.URL(r['href']).host}\n   {r.get('body', '')}" for i, r in enumerate(results, 1)]
    answer = f"Google's AI overview: {overview}\n\n" if overview else ""
    return answer + "\n".join(lines) + "\n\nThe snippets are short; read_result reads a whole page."


PRICES = [r'priceToPay[^>]*class="aok-offscreen">\s*([^<]+?)\s*</span>',
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
            page = requests.get(url, impersonate=browser, timeout=15)
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
    price = stated_price(page.text)
    heading = f"{results[number - 1].get('title', '')} — {url}" + (f"\nThe page's own price: {price}" if price else "")
    return f"{heading}\n\n{text[:LONGEST]}"
