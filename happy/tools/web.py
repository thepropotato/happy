"""Searching the web and reading what comes back, without opening anything on screen."""

import re
from typing import Annotated

import httpx

from happy.tools import tool
from happy.tools.browser import text_of

# EACH ENGINE MISSES SOME QUERIES AND DDGS'S "AUTO" ASKS A RANDOM FEW, SO THEY ARE ASKED ONE AT A TIME UNTIL ONE ANSWERS.
ENGINES = ("google", "bing", "yahoo", "duckduckgo", "brave", "mojeek")
LONGEST = 6000
results = []


@tool(say="Searching.", label="Searching for {query}")
def web_search(query: Annotated[str, "what to look up, in a few words"]):
    """Search the web to find out something: prices, news, facts, how-tos, anything not on this computer. Gives numbered results; read one with read_result."""
    from ddgs import DDGS
    from ddgs.exceptions import DDGSException

    global results
    results = []
    for engine in ENGINES:
        try:
            results = [r for r in DDGS(timeout=8).text(query, max_results=8, backend=engine) if r.get("href")]
        except DDGSException:
            continue
        if results:
            break
    if not results:
        return f"No search engine found anything for {query}. Try fewer or plainer words."
    lines = [f"{i}. {r.get('title', '')} — {httpx.URL(r['href']).host}\n   {r.get('body', '')}" for i, r in enumerate(results, 1)]
    return "\n".join(lines) + "\n\nThe snippets are short; read_result reads a whole page."


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
    price = stated_price(page.text)
    heading = f"{results[number - 1].get('title', '')} — {url}" + (f"\nThe page's own price: {price}" if price else "")
    return f"{heading}\n\n{text[:LONGEST]}"
