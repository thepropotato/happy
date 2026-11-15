from types import SimpleNamespace

import pytest

from happy.system import Failed, web_controls


@pytest.fixture
def chrome(monkeypatch):
    """agent-browser's replies, scripted, with every command it was given."""
    sent, page = [], {"value": ""}

    def run(*args, timeout=25):
        sent.append(args)
        if args[0] == "snapshot":
            return {"origin": "https://example.com/login", "refs": {
                "e2": {"role": "textbox", "name": "Email"}, "e1": {"role": "heading", "name": "Sign in"},
                "e10": {"role": "button", "name": "Sign in"}, "e3": {"role": "searchbox", "name": ""},
                "e4": {"role": "checkbox", "name": "Remember me"}}}
        if args[0] == "fill":
            page["value"] = args[-1]
            return {}
        if args[:2] == ("get", "value"):
            return {"value": page["value"]}
        if args[:2] == ("get", "title"):
            return {"title": "Sign in"}
        return {}

    monkeypatch.setattr(web_controls, "run", run)
    return sent


def test_snapshot_refs_become_controls_in_page_order(chrome):
    win = SimpleNamespace()
    found = web_controls.controls(win)
    assert [(c.kind, c.label, c.element) for c in found] == [
        ("text field", "Email", "@e2"), ("search field", "search field", "@e3"), ("checkbox", "Remember me", "@e4"),
        ("button", "Sign in", "@e10")]
    assert win.url == "https://example.com/login"


def test_fill_is_read_back(chrome):
    field = web_controls.Control("textbox", "Email", "", True, None, "@e2")
    assert web_controls.set_text(field, "jane@example.com", None)
    assert ("fill", "@e2", "--", "jane@example.com") in chrome


def test_text_that_looks_like_a_flag_stays_text(chrome):
    field = web_controls.Control("textbox", "Email", "", True, None, "@e2")
    web_controls.set_text(field, "--json", None)
    assert chrome[0] == ("fill", "@e2", "--", "--json")


def test_only_browsers_go_to_agent_browser(monkeypatch):
    monkeypatch.setattr(web_controls.shutil, "which", lambda name: "/usr/local/bin/agent-browser")
    monkeypatch.setattr(web_controls, "run", lambda *a, **k: {})
    monkeypatch.setattr(web_controls, "last_failure", 0.0)
    assert web_controls.usable("Google Chrome") and not web_controls.usable("Mail")


def test_a_failed_connection_waits_before_trying_again(monkeypatch):
    tries = []

    def refuse(*args, **kwargs):
        tries.append(args)
        raise Failed("no browser")

    monkeypatch.setattr(web_controls.shutil, "which", lambda name: "/usr/local/bin/agent-browser")
    monkeypatch.setattr(web_controls, "run", refuse)
    monkeypatch.setattr(web_controls, "last_failure", 0.0)
    assert not web_controls.usable("Google Chrome") and not web_controls.usable("Google Chrome")
    assert len(tries) == 1


def test_without_agent_browser_nothing_is_tried(monkeypatch):
    monkeypatch.setattr(web_controls.shutil, "which", lambda name: None)
    monkeypatch.setattr(web_controls, "run", lambda *a, **k: pytest.fail("ran agent-browser"))
    assert not web_controls.usable("Google Chrome")
