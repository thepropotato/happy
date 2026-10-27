"""A version asked for by name, like the Hindi trailer, opens that version and not its twin listed above it."""

from happy import tools
from happy.tools import apps, web

KANNADA = {"title": "Kantara Chapter 1 Official Trailer (Kannada) | Rishab Shetty", "href": "https://www.youtube.com/watch?v=Gx81NcPq2Lk", "host": "youtube.com"}
HINDI = {"title": "Kantara Chapter 1 Official Trailer (Hindi) | Rishab Shetty", "href": "https://www.youtube.com/watch?v=Hm42TbVw9Zs", "host": "youtube.com"}
APP = {"title": "Open in the YouTube app", "href": "https://www.youtube.com/app", "host": "youtube.com"}


class Page:
    def __init__(self, text):
        self.text = text


def opening(monkeypatch, where, said, found):
    opened = []
    monkeypatch.setattr(web, "results", [dict(r) for r in found])
    monkeypatch.setattr(apps.native, "open_path", lambda path, **kwargs: opened.append(path))
    monkeypatch.setattr(apps.webbrowser, "open", opened.append)
    tools.asked.set(said)
    return apps.open_link(where), opened


def test_results_listed_under_one_title_are_named_by_their_pages(monkeypatch):
    from curl_cffi import requests

    pages = {KANNADA["href"]: KANNADA["title"], HINDI["href"]: HINDI["title"]}
    monkeypatch.setattr(requests, "get", lambda url, **kwargs: Page(f"<title>{pages[url]} - YouTube</title>" if url in pages else "<html></html>"))
    found = [dict(r, title="Kantara Chapter 1 | Hombale Films - YouTube") for r in (KANNADA, HINDI)] + [dict(APP)]
    web.tell_apart(found)
    assert [r["title"] for r in found] == [KANNADA["title"], HINDI["title"], APP["title"]]


def test_a_video_google_retitled_is_named_by_its_page(monkeypatch):
    from curl_cffi import requests

    monkeypatch.setattr(requests, "get", lambda url, **kwargs: Page("<title>Veera Veera Lyrical (Telugu) | OM | Dhanush | Mammootty | Sai Pallavi - YouTube</title>"))
    found = [{"title": "OM | Dhanush | Mammootty", "href": "https://www.google.com/goto?url=CAESYw", "host": "36L+ views", "body": "YouTube · Divo Music 3:59"}]
    web.tell_apart(found)
    assert found[0]["title"] == "Veera Veera Lyrical (Telugu) | OM | Dhanush | Mammootty | Sai Pallavi"


def test_a_consent_page_does_not_rename_a_result(monkeypatch):
    from curl_cffi import requests

    monkeypatch.setattr(requests, "get", lambda url, **kwargs: Page("<title>Before you continue to YouTube</title>"))
    found = [dict(KANNADA)]
    web.tell_apart(found)
    assert found[0]["title"] == KANNADA["title"]


def test_a_page_title_that_says_less_never_replaces_googles(monkeypatch):
    from curl_cffi import requests

    pages = {"https://www.amazon.in/dp/B0CY5HVDS2": "Sony PlayStation5 Gaming Console (Slim) | Disc Edition - 1TB : Amazon.in: Video Games",
             "https://www.reddit.com/r/PS5/comments/1": "Reddit"}
    monkeypatch.setattr(requests, "get", lambda url, **kwargs: Page(f"<title>{pages[url]}</title>"))
    found = [{"title": "Sony PlayStation5 Gaming Console (Slim) | Disc Edition", "href": "https://www.amazon.in/dp/B0CY5HVDS2"},
             {"title": "I ordered PS5 Slim Disc Edition from Amazon but ...", "href": "https://www.reddit.com/r/PS5/comments/1"}]
    web.tell_apart(found)
    assert [r["title"] for r in found] == [pages["https://www.amazon.in/dp/B0CY5HVDS2"], "I ordered PS5 Slim Disc Edition from Amazon but ..."]


def test_a_result_read_right_after_the_search_is_not_fetched_again(monkeypatch):
    from curl_cffi import requests

    fetches = []
    words = "The PlayStation 5 Slim with a 1TB drive. " * 20

    def get(url, **kwargs):
        fetches.append(url)
        page = Page(f"<html><head><title>PS5 Slim 1TB</title></head><body><p>{words}</p></body></html>")
        page.url, page.status_code = url, 200
        return page

    monkeypatch.setattr(requests, "get", get)
    found = [{"title": "PS5 Slim", "href": "https://www.amazon.in/dp/B0CY5HVDS2"}]
    web.tell_apart(found)
    monkeypatch.setattr(web, "results", found)
    assert web.read_result(1).startswith("PS5 Slim 1TB") and len(fetches) == 1


def test_the_version_they_named_opens_instead_of_its_twin(monkeypatch):
    said, opened = opening(monkeypatch, KANNADA["href"], "open the hindi one for me", [KANNADA, HINDI])
    assert opened == [HINDI["href"]] and "(Hindi)" in said


def test_the_version_picked_opens_when_it_is_the_one_named(monkeypatch):
    _, opened = opening(monkeypatch, "1", "open the kannada trailer", [KANNADA, HINDI])
    assert opened == [KANNADA["href"]]
    _, opened = opening(monkeypatch, "1", "open the first one", [KANNADA, HINDI])
    assert opened == [KANNADA["href"]]


def test_a_result_that_only_shares_their_words_never_takes_over(monkeypatch):
    _, opened = opening(monkeypatch, "1", "open the kantara trailer in the youtube app", [KANNADA, APP])
    assert opened == [KANNADA["href"]]


def test_a_result_named_by_its_title_opens_the_result(monkeypatch):
    _, opened = opening(monkeypatch, "Kantara Chapter 1 Official Trailer (Hindi)", "open the hindi trailer", [KANNADA, HINDI])
    assert opened == [HINDI["href"]]


def test_a_site_or_other_words_still_open_as_before(monkeypatch):
    _, opened = opening(monkeypatch, "youtube.com", "open youtube", [KANNADA, HINDI])
    assert opened == ["https://youtube.com"]
    _, opened = opening(monkeypatch, "lofi music", "open lofi music", [KANNADA, HINDI])
    assert opened == ["https://www.google.com/search?q=lofi+music"]
