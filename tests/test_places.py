"""A misheard town name still finds the town, from the GeoNames list kept under ~/.happy/places."""

import pytest

from happy.tools import places

pytestmark = pytest.mark.skipif(not (places.FOLDER / "cities5000.txt").exists(), reason="the town list has not been downloaded")


@pytest.mark.parametrize("said, town", [
    ("lundon", "London"),
    ("melbun australia currently", "Melbourne"),
    ("edinbra", "Edinburgh"),
    ("san fransisco", "San Francisco"),
    ("cambridge uk", "Cambridge"),
    ("wellingtun new zealand", "Wellington"),
    ("munich germany", "Munich"),
])
def test_a_misheard_town_is_found_by_how_it_sounds(said, town):
    assert places.guess(said)[0].startswith(town)


def test_nonsense_finds_nothing(monkeypatch):
    from happy.tools import web

    monkeypatch.setattr(web, "search", lambda query: ("", []))
    assert places.guess("asdfghjk") is None


# THE OVERVIEW NAMES THE TOWN WHILE THE TITLES ARE FULL OF A STREET THAT SHARES PART OF THE NAME.
NAMED = (" It looks like you are searching for Edinburgh, the capital city of Scotland.",
         [{"title": "Bruh Street Cafe, Leith Walk", "body": ""}, {"title": "Bruh Street parking - Glasgow", "body": ""}])
# THE RESULTS ARE FULL OF A REAL TOWN THAT SOUNDS LITTLE LIKE WHAT WAS SAID.
ELSEWHERE = (" Auckland is the largest city in New Zealand.",
             [{"title": "Auckland travel guide", "body": "Things to do in Auckland."}, {"title": "Auckland weather", "body": ""}])


def test_a_name_that_sounds_like_nothing_is_taken_from_a_web_search(monkeypatch):
    from happy.tools import web

    monkeypatch.setattr(web, "search", lambda query: NAMED)
    assert places.searched("edin bruh scotland")["name"] == "Edinburgh"


def test_a_town_the_search_is_full_of_is_not_taken_when_it_sounds_unlike_what_was_said(monkeypatch):
    from happy.tools import web

    monkeypatch.setattr(web, "search", lambda query: ELSEWHERE)
    assert places.searched("wellingtun") is None
