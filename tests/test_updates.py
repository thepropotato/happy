"""An installed Happy finds a newer release, refuses one that does not match its checksum, and installs only when quiet."""

import hashlib

import httpx
import pytest

from happy import updates


def test_versions_compare_by_number_not_by_text():
    assert updates.newer("1.0.10", "1.0.9")
    assert updates.newer("1.1.0", "1.0.0")
    assert not updates.newer("1.0.0", "1.0.0")
    assert not updates.newer("0.9.9", "1.0.0")
    assert updates.newer("v1.2.0".lstrip("v"), "1.1.9")


class Reply:
    def __init__(self, body):
        self.body = body
        self.text = body.decode() if isinstance(body, bytes) else body
        self.headers = {"content-length": str(len(body))}

    def raise_for_status(self):
        pass

    def iter_bytes(self, size):
        yield self.body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


def serve(monkeypatch, tmp_path, payload, published):
    monkeypatch.setattr(updates, "DOWNLOADS", tmp_path)
    monkeypatch.setattr(httpx, "get", lambda url, **_: Reply(f"{published}  {updates.ASSET}\n"))
    monkeypatch.setattr(httpx, "stream", lambda method, url, **_: Reply(payload))
    return {"version": "9.9.9", "url": "https://example.invalid/file", "sums": "https://example.invalid/sums"}


def test_a_download_matching_its_checksum_is_kept(monkeypatch, tmp_path):
    payload = b"the new happy"
    release = serve(monkeypatch, tmp_path, payload, hashlib.sha256(payload).hexdigest())
    kept = updates.fetch(release)
    assert kept.read_bytes() == payload


def test_a_download_that_does_not_match_is_thrown_away(monkeypatch, tmp_path):
    release = serve(monkeypatch, tmp_path, b"something else", hashlib.sha256(b"the new happy").hexdigest())
    with pytest.raises(ValueError):
        updates.fetch(release)
    assert not list(tmp_path.iterdir())


def test_an_update_waits_until_happy_has_been_quiet(monkeypatch, tmp_path):
    monkeypatch.setattr(updates, "current", lambda: "1.0.0")
    monkeypatch.setattr(updates, "installed_at", lambda: tmp_path)
    monkeypatch.setattr(updates, "remember", lambda state: None)
    monkeypatch.setattr(updates, "recalled", lambda: {})
    monkeypatch.setattr(updates, "latest", lambda: {"version": "1.0.1"})
    monkeypatch.setattr(updates, "fetch", lambda release, progress: tmp_path / "Happy.dmg")
    installed = []
    monkeypatch.setattr(updates, "install", lambda path: installed.append(path) or True)
    quiet = iter([0, 30, 301])
    left = []
    keeper = updates.Keeper(quiet_for=lambda: next(quiet), quit=lambda: left.append(True))
    keeper.wake.wait = lambda seconds=None: False
    keeper.cycle()
    assert installed == [tmp_path / "Happy.dmg"]
    assert left == [True]


def test_with_updates_off_a_new_version_is_only_mentioned(monkeypatch, tmp_path):
    from happy.config import Config

    monkeypatch.setattr(updates, "current", lambda: "1.0.0")
    monkeypatch.setattr(updates, "installed_at", lambda: tmp_path)
    monkeypatch.setattr(updates, "recalled", lambda: {})
    monkeypatch.setattr(updates, "latest", lambda: {"version": "1.0.1"})
    monkeypatch.setattr(Config, "get", lambda self, key, default=None: False if key == "auto_update" else default)
    monkeypatch.setattr(updates, "fetch", lambda *_: pytest.fail("nothing is downloaded with updates off"))
    keeper = updates.Keeper(quiet_for=lambda: 10_000, quit=lambda: pytest.fail("nothing is installed with updates off"))
    keeper.cycle()
    assert keeper.state["state"] == "available"


def test_a_copy_run_from_source_never_replaces_itself(monkeypatch):
    monkeypatch.setattr(updates, "current", lambda: "1.0.0")
    monkeypatch.setattr(updates, "installed_at", lambda: None)
    monkeypatch.setattr(updates, "recalled", lambda: {})
    monkeypatch.setattr(updates, "latest", lambda: {"version": "1.0.1"})
    keeper = updates.Keeper(quiet_for=lambda: 10_000, quit=lambda: pytest.fail("a source copy never quits to update"))
    keeper.cycle()
    assert keeper.state["state"] == "available"
    assert "git pull" in keeper.state["text"]
