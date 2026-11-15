import asyncio
import types

from happy import learned, tools
from happy.app import Happy


def step(tool, args, result, ok=True):
    return {"tool": tool, "args": args, "result": result, "ok": ok}


CLICKED = step("use_app", {"action": "click", "target": "Send", "app": "Mail"}, "Pressed the button Send in Mail. The window closed.")


def test_actions_that_worked_are_kept_and_found_by_the_same_words():
    assert learned.learn("Send this in Mail, please!", [CLICKED])
    assert learned.match("send this in mail") == [{"tool": "use_app", "args": CLICKED["args"]}]


def test_a_look_is_not_kept_but_does_not_stop_the_rest():
    look = step("use_app", {"action": "look", "app": "Mail"}, "Mail, window Draft. Its controls…")
    assert learned.learn("send this in mail", [look, CLICKED])
    assert [s["args"]["action"] for s in learned.match("send this in mail")] == ["click"]


def test_a_step_that_could_not_be_checked_is_not_kept():
    unseen = step("use_app", {"action": "click", "target": "Send"}, "Pressed the button Send in Mail. Nothing in the window changed that could be seen, so check before saying it worked.")
    assert not learned.learn("send this in mail", [unseen])


def test_reading_and_sending_are_never_kept():
    assert not learned.learn("tell mom I'm late", [step("whatsapp_send", {"to": "mom"}, "Sent.")])
    assert not learned.learn("what's the weather", [step("weather", {}, "Clear, 30°C.")])
    assert not learned.learn("fix the tests", [step("hand_off_coding", {}, "Opened Claude Code.")])


def test_a_failed_step_is_not_kept():
    assert not learned.learn("click archive", [step("use_app", {"action": "click", "target": "archive"}, "Nothing called archive in Mail.")])


def test_forget_lets_it_go():
    learned.learn("send this in mail", [CLICKED])
    assert learned.forget("send this in mail") and learned.match("send this in mail") is None


class Face:
    def __init__(self):
        self.rows = []

    def began(self, call, tool, label, args):
        self.rows.append(("began", tool, label))

    def ended(self, call, tool, label, args, result, ok):
        self.rows.append(("ended", tool, ok))

    def reply(self, text):
        self.said = text

    def state(self, state):
        pass


def happy_with(monkeypatch, results):
    calls = []

    async def call(name, args):
        calls.append((name, args))
        return results.pop(0)

    monkeypatch.setattr(tools, "call", call)
    tools.load()
    me = types.SimpleNamespace(face=Face(), steps=[], reply="", backend=None, plain=Happy.plain, say=lambda text: None)
    return me, calls


def test_a_replay_shows_each_step_and_says_what_happened(monkeypatch):
    learned.learn("send this in mail", [CLICKED])
    me, calls = happy_with(monkeypatch, ["Pressed the button Send in Mail. The window closed."])
    assert asyncio.run(Happy.replay(me, learned.match("send this in mail"), "send this in mail", 0.0))
    assert calls == [("use_app", CLICKED["args"])]
    assert me.face.rows == [("began", "use_app", "Clicking Send in Mail"), ("ended", "use_app", True)]
    assert me.reply == "Pressed the button Send in Mail. The window closed."


def test_a_replay_that_stops_working_is_forgotten(monkeypatch):
    learned.learn("send this in mail", [CLICKED])
    me, _ = happy_with(monkeypatch, ["Nothing called Send in Mail. Its controls include: Archive."])
    assert not asyncio.run(Happy.replay(me, learned.match("send this in mail"), "send this in mail", 0.0))
    assert learned.match("send this in mail") is None and me.face.rows[-1] == ("ended", "use_app", False)


def test_a_correction_forgets_what_it_corrects():
    learned.learn("open the downloads folder", [step("open_file", {"what": "downloads"}, "Opened Downloads in Finder.")])
    me = types.SimpleNamespace(last_spoken=("open the downloads folder", __import__("time").monotonic()), correcting=Happy.correcting)
    Happy.corrected(me, "no, the documents folder", "woken")
    assert learned.match("open the downloads folder") is None
