"""Where this computer is comes from Location Services when allowed, and an internet address is said to be approximate."""

import pytest

from happy.system import native
from happy.tools import places, weather

pytestmark = pytest.mark.skipif(not (places.FOLDER / "cities5000.txt").exists(), reason="the town list has not been downloaded")


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    monkeypatch.setitem(weather.found_at, "where", None)


def test_location_services_names_the_town_the_mac_is_in(monkeypatch):
    monkeypatch.setattr(native, "locate", lambda: (52.205, 0.119, 65.0), raising=False)
    said = weather.location()
    assert said.startswith("Cambridge, England, United Kingdom") and "Location Services" in said and "approximate" not in said


def test_an_internet_address_is_said_to_be_approximate(monkeypatch):
    def off():
        raise native.Failed("Location Services is off for Happy")

    class Answer:
        def json(self):
            return {"city": "Springfield", "loc": "39.80,-89.64"}

    monkeypatch.setattr(native, "locate", off, raising=False)
    monkeypatch.setattr(weather.httpx, "get", lambda *a, **k: Answer())
    said = weather.location()
    assert said.startswith("Springfield") and "approximate" in said and "is off for Happy" in said


def test_a_suburb_gives_its_city():
    assert places.nearest(-41.29, 174.78)[0].startswith("Wellington")
