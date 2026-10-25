"""Happy's own WhatsApp group, against a fake bridge: only the owner's new messages are requests, never Happy's answers."""

import time

import pytest

from happy.integrations import own_chat, whatsapp


class Reply:
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


class Settings:
    """A config held in memory, so the tests never touch the real one."""

    def __init__(self, **values):
        self.values = {"name": "Happy", "colour": "#658761", **values}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value

    def save(self):
        pass


def chat_for(settings):
    return own_chat.Chat(settings, load=lambda: settings)


@pytest.fixture
def bridge(monkeypatch):
    state = {"groups": [{"id": "1@g.us", "name": "Happy"}], "messages": [], "pushed": [], "sent": [], "made": [],
             "renamed": [], "photos": []}

    def get(url, params=None, timeout=None):
        if url.endswith("/groups"):
            return Reply(state["groups"])
        if url.endswith("/pushed"):
            return Reply(state["pushed"])
        return Reply(list(reversed(state["messages"])))

    def post(url, json=None, timeout=None):
        if url.endswith("/create-group"):
            state["made"].append(json["name"])
            state["groups"].append({"id": "2@g.us", "name": json["name"]})
            return Reply({"id": "2@g.us"})
        if url.endswith("/set-group-name"):
            state["renamed"].append(json["name"])
            next(g for g in state["groups"] if g["id"] == json["group"])["name"] = json["name"]
            return Reply({"id": json["group"]})
        if url.endswith("/set-group-photo"):
            state["photos"].append(json["group"])
            return Reply({"id": json["group"]})
        state["sent"].append(json["message"])
        ident = f"sent{len(state['sent'])}"
        state["pushed"].append({"id": ident})
        state["messages"].append({"id": ident, "fromMe": True, "body": json["message"], "timestamp": time.time()})
        return Reply({"success": True, "messageId": ident})

    monkeypatch.setattr(own_chat.httpx, "get", get)
    monkeypatch.setattr(own_chat.httpx, "post", post)
    monkeypatch.setattr(whatsapp, "listening", lambda: True)
    monkeypatch.setattr("happy.ui.picture.smile_jpeg", lambda colour: b"jpeg")
    return state


def test_only_the_owners_new_messages_are_requests(bridge):
    chat = chat_for(Settings())
    now = time.time()
    bridge["messages"] = [
        {"id": "old", "fromMe": True, "body": "from last week", "timestamp": now - 86400},
        {"id": "a", "fromMe": True, "body": "how much battery is left", "timestamp": now + 1},
        {"id": "b", "fromMe": False, "body": "someone else", "timestamp": now + 2},
        {"id": "c", "fromMe": True, "body": "  ", "timestamp": now + 3},
    ]
    assert chat.requests() == ["how much battery is left"]
    assert chat.requests() == []


def test_happys_own_answer_is_never_read_back_as_a_request(bridge):
    chat = chat_for(Settings())
    chat.find()
    assert chat.send("Battery is at 80%.")
    assert chat.requests() == []


def test_the_group_is_made_once_when_there_is_none(bridge):
    bridge["groups"] = []
    settings = Settings()
    chat = chat_for(settings)
    assert chat.find() == "2@g.us"
    assert bridge["made"] == ["Happy"]
    assert bridge["photos"] == ["2@g.us"]
    assert settings.get("whatsapp.own_chat_id") == "2@g.us"
    assert bridge["sent"][0].startswith("This is my chat.")
    assert chat.requests() == []


def test_a_new_name_renames_the_same_group_and_a_new_colour_repaints_it(bridge):
    settings = Settings()
    chat = chat_for(settings)
    assert chat.find() == "1@g.us"
    assert bridge["photos"] == ["1@g.us"]
    settings.set("name", "Daemon")
    settings.set("colour", "#3b6ea8")
    chat.synced = 0
    assert chat.find() == "1@g.us"
    assert bridge["renamed"] == ["Daemon"]
    assert bridge["photos"] == ["1@g.us", "1@g.us"]
    chat.synced = 0
    chat.find()
    assert bridge["renamed"] == ["Daemon"] and len(bridge["photos"]) == 2
