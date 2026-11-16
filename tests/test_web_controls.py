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


@pytest.fixture
def installed(monkeypatch, tmp_path):
    """agent-browser found, and a Chrome profile in a throwaway folder with remote debugging off."""
    monkeypatch.setattr(web_controls, "binary", lambda: "/usr/local/bin/agent-browser")
    monkeypatch.setitem(web_controls.PROFILES, web_controls.sys.platform, [tmp_path])
    monkeypatch.setattr(web_controls, "last_failure", 0.0)
    monkeypatch.setattr(web_controls, "told", False)
    return tmp_path


def let_in(profile):
    (profile / "DevToolsActivePort").write_text("9222\n/devtools/browser/x")


def test_only_browsers_go_to_agent_browser(installed, monkeypatch):
    let_in(installed)
    monkeypatch.setattr(web_controls, "run", lambda *a, **k: {})
    assert web_controls.usable("Google Chrome") and not web_controls.usable("Mail")


def test_a_failed_connection_waits_before_trying_again(installed, monkeypatch):
    tries = []

    def refuse(*args, **kwargs):
        tries.append(args)
        raise Failed("no browser")

    let_in(installed)
    monkeypatch.setattr(web_controls, "run", refuse)
    assert not web_controls.usable("Google Chrome") and not web_controls.usable("Google Chrome")
    assert len(tries) == 1


def test_without_agent_browser_nothing_is_tried(installed, monkeypatch):
    let_in(installed)
    monkeypatch.setattr(web_controls, "binary", lambda: None)
    monkeypatch.setattr(web_controls, "run", lambda *a, **k: pytest.fail("ran agent-browser"))
    assert not web_controls.usable("Google Chrome")


def test_chrome_without_remote_debugging_is_never_asked(installed, monkeypatch):
    # ASKING WOULD WAIT ON CHROME'S PROMPT OR FAIL; THE PROFILE ALREADY SAYS IT IS OFF.
    monkeypatch.setattr(web_controls, "run", lambda *a, **k: pytest.fail("ran agent-browser"))
    assert not web_controls.usable("Google Chrome")


def test_the_way_in_is_said_once(installed):
    first = web_controls.not_let_in("Google Chrome")
    assert "has not let Happy" in first and web_controls.not_let_in("Google Chrome") == ""


def test_nothing_is_said_once_chrome_lets_it_in(installed):
    let_in(installed)
    assert web_controls.not_let_in("Google Chrome") == ""


def test_nothing_is_said_for_other_apps(installed):
    assert web_controls.not_let_in("Finder") == ""


def test_setup_s_place_is_found_without_a_path(monkeypatch, tmp_path):
    placed = tmp_path / ".local/bin/agent-browser"
    placed.parent.mkdir(parents=True)
    placed.write_text("")
    monkeypatch.setattr(web_controls.shutil, "which", lambda name: None)
    monkeypatch.setattr(web_controls.Path, "home", lambda: tmp_path)
    assert web_controls.binary() == str(placed)


def test_the_snapshot_text_sets_page_order_and_state(monkeypatch):
    # AS REAL CHROME RETURNED IT ON 2026-11-15: REF NUMBERS ARE NOT PAGE ORDER.
    snapshot = ('- heading "Happy test" [level=1, ref=e1]\n- textbox "Name" [ref=e4]: John Doe\n'
                '- checkbox "Remember me" [checked=true, ref=e2]\n- button "Send" [disabled=true, ref=e3]')
    refs = {"e1": {"name": "Happy test", "role": "heading"}, "e2": {"name": "Remember me", "role": "checkbox"},
            "e3": {"name": "Send", "role": "button"}, "e4": {"name": "Name", "role": "textbox"}}
    monkeypatch.setattr(web_controls, "run", lambda *a, **k: {"snapshot": snapshot, "refs": refs})
    found = web_controls.controls(SimpleNamespace())
    assert [(c.label, c.value, c.enabled) for c in found] == [
        ("Name", "John Doe", True), ("Remember me", "checked=true", True), ("Send", "disabled=true", False)]


def test_the_port_falls_back_to_chromes_own(installed):
    assert web_controls.port() == "9222"
    (installed / "DevToolsActivePort").write_text("9333\n/devtools/browser/x")
    assert web_controls.port() == "9333"
