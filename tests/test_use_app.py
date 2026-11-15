from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from happy import system
from happy.tools import screen


@dataclass
class Control:
    role: str
    label: str
    value: str = ""
    enabled: bool = True
    field: bool = False
    listed: bool = True
    kind: str = "button"
    frame: tuple = (0, 0, 10, 10)


class Fake:
    """A stand-in for one OS's controls module: one window, the controls given, and a log of what was done."""

    def __init__(self, found, pid=7, app="Mail"):
        self.found, self.done, self.name = found, [], "Draft"
        self.win = SimpleNamespace(app=app, title="Draft", pid=pid, front=False)

    def window(self, app=""):
        return self.win

    def controls(self, win):
        return self.found

    def press(self, control, win):
        self.done.append(("press", control.label))
        self.name = "Sent"
        return "pressed"

    def set_text(self, control, text, win):
        self.done.append(("type", control.label, text))
        return True

    def bring_forward(self, win):
        self.done.append(("forward",))

    def menu(self, win, path):
        self.done.append(("menu", path))
        return path

    def focused_field(self, win):
        return None

    def title(self, win):
        return self.name

    def alive(self, control):
        return True


@pytest.fixture
def mail(monkeypatch):
    fake = Fake([Control("AXButton", "Send"), Control("AXButton", "Send Later"), Control("AXTextField", "To", field=True, kind="text field"),
                 Control("AXButton", "Delete", enabled=False), Control("AXStaticText", "Sending options", listed=False, kind="text")])
    monkeypatch.setattr(system, "controls", fake)
    from happy.system import web_controls

    # NO TEST REACHES THE PERSON'S REAL CHROME, EVEN WITH agent-browser INSTALLED.
    monkeypatch.setattr(web_controls, "usable", lambda app: False)
    monkeypatch.setattr(screen.native, "trusted", lambda: True)
    screen.listing.update(pid=None, items=[])
    return fake


def test_the_whole_name_beats_a_longer_one():
    found = [Control("AXButton", "Send Later"), Control("AXButton", "Send")]
    assert [c.label for c in screen.ranked(found, "send")] == ["Send", "Send Later"]


def test_a_field_wins_when_typing():
    found = [Control("AXButton", "Search"), Control("AXSearchField", "Search", field=True)]
    assert screen.ranked(found, "search", fields=True)[0].field


def test_every_word_matches_in_any_order():
    assert screen.ranked([Control("AXButton", "Reply All")], "all reply")[0].label == "Reply All"


def test_kind_words_drop_away_when_nothing_has_them():
    found = [Control("AXButton", "Send"), Control("AXButton", "New tab")]
    assert screen.ranked(found, "the send button")[0].label == "Send"
    assert screen.ranked(found, "new tab")[0].label == "New tab"


def test_click_presses_and_says_what_changed(mail):
    said = screen.use_app("click", target="send", app="mail")
    assert mail.done == [("press", "Send")]
    assert "The window is now Sent." in said


def test_a_greyed_out_control_is_not_pressed(mail):
    said = screen.use_app("click", target="delete")
    assert mail.done == [] and "greyed out" in said


def test_a_number_means_the_last_look_at_that_app(mail):
    listed = screen.use_app("look")
    assert "1. button Send" in listed and "Sending options" not in listed
    screen.use_app("click", target="2")
    assert mail.done == [("press", "Send Later")]


def test_a_number_from_another_app_is_refused(mail):
    screen.use_app("look")
    mail.win.pid = 99
    said = screen.use_app("click", target="1")
    assert mail.done == [] and "Look at it first" in said


def test_type_goes_into_the_named_field(mail):
    said = screen.use_app("type", target="to", text="jane@example.com")
    assert mail.done == [("type", "To", "jane@example.com")] and "jane@example.com" in said


def test_nothing_by_that_name_lists_what_is_there(mail):
    said = screen.use_app("click", target="archive")
    assert "Nothing called archive" in said and "Send" in said


def test_menu_brings_the_app_forward_first(mail):
    said = screen.use_app("menu", target="Message > Send Again")
    assert mail.done == [("forward",), ("menu", ["Message", "Send Again"])] and "Message > Send Again" in said


def test_the_panel_row_names_the_step():
    from happy import tools

    tools.load()
    show = tools.REGISTRY["use_app"].show
    assert show({"action": "click", "target": "Send", "app": "Mail"}) == "Clicking Send in Mail"
    assert show({"action": "look"}) == "Looking at the controls"


def test_a_menu_path_sent_as_a_click_goes_to_the_menu(mail):
    screen.use_app("click", target="View > as List", app="finder")
    assert ("menu", ["View", "as List"]) in mail.done


def test_their_words_set_how_far_to_scroll(mail, monkeypatch):
    from happy import tools

    went = []
    monkeypatch.setattr(mail, "scroll", lambda win, where: went.append(where) or 1.0, raising=False)
    token = tools.asked.set("scroll to the bottom of this window")
    try:
        said = screen.use_app("scroll", target="down")
    finally:
        tools.asked.reset(token)
    assert went == ["bottom"] and "at the bottom" in said


def test_a_page_in_chrome_goes_through_agent_browser(mail, monkeypatch):
    from happy.system import web_controls

    sent = []

    def run(*args, timeout=25):
        sent.append(args)
        if args[0] == "snapshot":
            return {"refs": {"e1": {"role": "checkbox", "name": "Remember me"}}}
        return {"title": "Sign in", "visible": True}

    monkeypatch.setattr(web_controls, "usable", lambda app: True)
    monkeypatch.setattr(web_controls, "run", run)
    mail.win.app = "Google Chrome"
    said = screen.use_app("click", target="remember me box", app="chrome")
    assert ("click", "@e1") in sent and mail.done == []
    assert "Remember me" in said
