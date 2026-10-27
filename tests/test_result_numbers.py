"""A search result's number means one page for good, so a later search never hands it to another."""

from happy import tools
from happy.tools import apps, web

FLIPKART = [{"title": "SONY Playstation5 Digital Edition (Slim) 1 TB : Flipkart.com", "href": "https://www.flipkart.com/sony-ps5-digital/p/itm6a1c0e5b2f7d1", "host": "flipkart.com"},
            {"title": "SONY PS5 Console Digital - Fortnite Bundle (Slim) 1 TB : Flipkart.com", "href": "https://www.flipkart.com/sony-ps5-fortnite/p/itm1660d204e39f8", "host": "flipkart.com"}]
AMAZON = [{"title": "Sony PlayStation 5 Digital Edition (Slim) : Amazon.in", "href": "https://www.amazon.in/dp/B0CY5QW186", "host": "amazon.in"},
          {"title": "Amazon.in: Sony India: PS5 Console", "href": "https://www.amazon.in/stores/PlayStation/page/5D2B6F4E", "host": "amazon.in"}]


def searched(monkeypatch, *listings):
    answers = iter(listings)
    monkeypatch.setattr(web, "results", [])
    monkeypatch.setattr(web, "google", lambda query: ("", [dict(r) for r in next(answers)]))
    monkeypatch.setattr(web, "tell_apart", lambda found: None)
    return [web.web_search(f"search {i}") for i in range(len(listings))]


def test_a_later_search_numbers_on_from_the_last(monkeypatch):
    first, second = searched(monkeypatch, FLIPKART, AMAZON)
    assert first.startswith("1. SONY Playstation5") and "\n2. SONY PS5 Console Digital - Fortnite" in first
    assert second.startswith("3. Sony PlayStation 5 Digital Edition") and "\n4. Amazon.in: Sony India" in second


def test_a_number_from_an_earlier_search_opens_its_own_page(monkeypatch):
    searched(monkeypatch, FLIPKART, AMAZON)
    opened = []
    monkeypatch.setattr(apps.native, "open_path", lambda path, **kwargs: opened.append(path))
    monkeypatch.setattr(apps.webbrowser, "open", opened.append)
    tools.asked.set("show me the flipkart ps5 page")
    said = apps.open_link("2")
    assert opened == [FLIPKART[1]["href"]] and "Fortnite" in said


def test_a_flipkart_page_gives_its_own_price():
    page = '<script>window.__INITIAL_STATE__={"ppd":{"fsp":44990,"finalPrice":44990,"mrp":44990,"nepPrice":42740}}</script>'
    assert web.stated_price(page) == "44990"


def test_a_page_held_from_an_earlier_search_is_let_go(monkeypatch):
    monkeypatch.setattr(web, "results", [])
    monkeypatch.setattr(web, "google", lambda query: ("", [dict(r) for r in AMAZON]))
    monkeypatch.setattr(web, "tell_apart", lambda found: [r.setdefault("fetched", object()) for r in found])
    web.web_search("first")
    web.web_search("second")
    assert [("fetched" in r) for r in web.results] == [False, False, True, True]
