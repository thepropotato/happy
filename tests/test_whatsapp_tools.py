"""Reading a chat says whose the last word was, and a name offered back to the person is one a lookup takes."""

import asyncio

from happy.tools import whatsapp
from whatsapp_server import nearing

CHAT = [
    {"timestamp": 100, "fromMe": False, "from": "Jane Doe", "body": "See you at six"},
    {"timestamp": 200, "fromMe": True, "body": "Okay"},
]


def read(monkeypatch, chat, count=10):
    async def ask(name, **args):
        found = [m for m in CHAT if not (args.get("received_only") and m["fromMe"])]
        return sorted(found, key=lambda m: -m["timestamp"])[:args["limit"]]

    monkeypatch.setattr(whatsapp, "ask", ask)
    monkeypatch.setattr(whatsapp, "me", lambda: "John")
    return asyncio.run(whatsapp.whatsapp_read(chat=chat, count=count))


def test_their_last_message_is_found_when_the_newest_is_mine(monkeypatch):
    said = read(monkeypatch, "Jane Doe", count=1)
    assert "The newest message is John's own, not Jane Doe's." in said
    assert "The last message from Jane Doe:" in said and "See you at six" in said
    assert "John: Okay" in said


def test_a_name_with_its_note_on_is_shown_bare(monkeypatch):
    said = read(monkeypatch, "Jane Doe (WhatsApp profile name Notjane)")
    assert said.startswith("Chat with Jane Doe, newest last.")


def test_one_person_is_offered_once_under_the_name_a_lookup_takes():
    said = nearing.missed("Jan", [("Jane Doe", "Notjane"), ("Janet", "")])
    assert "'Jane Doe' (WhatsApp profile name Notjane), 'Janet'" in said


class Sends:
    def __init__(self, monkeypatch, said, earlier=()):
        from happy import history, tools
        from happy.integrations import whatsapp as bridge

        self.sent, self.posted, self.noted = [], [], []
        tools.asked.set(said)
        monkeypatch.setattr(history, "recent", lambda limit=200: [{"request": r, "reply": a} for r, a in earlier])
        monkeypatch.setattr(bridge, "own_chat", lambda: "123@g.us")

        async def ask(name, **args):
            self.sent.append((name, args))
            return {"success": True}

        async def call(server, name, args):
            self.noted.append(args)

        monkeypatch.setattr(whatsapp, "ask", ask)
        monkeypatch.setattr(whatsapp, "post", lambda path, body: self.posted.append((path, body)) or {"success": True})
        monkeypatch.setattr(whatsapp.hub, "call", call)
        monkeypatch.setattr("happy.tools.notes.note", lambda fact: self.noted.append(fact))
        monkeypatch.setattr("whatsapp_server.contacts.loaded_facts", lambda: {"sis": {"whatsapp": "Jane Doe"}})


def send(**args):
    return asyncio.run(whatsapp.whatsapp_send(**args))


def test_a_send_to_someone_never_named_is_held(monkeypatch):
    sends = Sends(monkeypatch, "send it here", earlier=[("send it here", ""), ("do i have my resume", "Yes, in Downloads.")])
    said = send(to="Jane Doe", message="Send it here")
    assert said.startswith("Not sent") and sends.sent == []


def test_a_name_from_the_turn_before_or_a_kept_nickname_is_enough(monkeypatch):
    sends = Sends(monkeypatch, "tell her i'm coming", earlier=[("any word from jane?", "Jane Doe said see you at six.")])
    send(to="Jane Doe", message="I'm coming")
    Sends(monkeypatch, "tell my sis hi")
    send(to="Jane Doe", message="hi")
    assert len(sends.sent) == 1


def test_here_sends_the_file_to_their_own_chat(monkeypatch, tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"%PDF")
    sends = Sends(monkeypatch, "send it here")
    send(to="me", file=str(resume))
    assert sends.posted == [("/send-media", {"to": "123@g.us", "url": str(resume), "caption": "", "filename": "resume.pdf"})]


def test_only_a_relationship_they_said_is_remembered(monkeypatch):
    sends = Sends(monkeypatch, "message jane doe hi")
    send(to="Jane Doe", message="hi", called="brother")
    assert sends.noted == []
    sends = Sends(monkeypatch, "tell my brother jane doe hi")
    send(to="Jane Doe", message="hi", called="brother")
    assert sends.noted


def test_a_relationship_they_said_names_the_contact_it_was_looked_up_as(monkeypatch):
    sends = Sends(monkeypatch, "tell my brother to come fast")
    send(to="John Doe", message="Come fast", called="brother")
    assert len(sends.sent) == 1


def read_group(monkeypatch, messages, **args):
    async def ask(name, **asked):
        return sorted(messages, key=lambda m: -m["timestamp"])[:asked["limit"]]

    monkeypatch.setattr(whatsapp, "ask", ask)
    monkeypatch.setattr(whatsapp, "me", lambda: "John")
    return asyncio.run(whatsapp.whatsapp_read(chat="Office", **args))


def test_reactions_do_not_use_up_a_read(monkeypatch):
    group = [{"timestamp": 100 + i, "fromMe": False, "from": "Jane Doe", "body": f"line {i}"} for i in range(3)]
    group += [{"timestamp": 200 + i, "fromMe": False, "from": "Jane Doe", "type": "reaction", "body": "😂"} for i in range(5)]
    said = read_group(monkeypatch, group, count=3)
    assert "😂" not in said and all(f"line {i}" in said for i in range(3))


def test_a_day_is_read_whole_oldest_first_without_reactions(monkeypatch):
    start, _ = whatsapp.day_bounds("today")
    group = [{"timestamp": start - 60, "fromMe": False, "from": "Jane Doe", "body": "yesterday's"},
             {"timestamp": start + 60, "fromMe": False, "from": "Jane Doe", "body": "first today"},
             {"timestamp": start + 120, "fromMe": False, "from": "Jane Doe", "type": "reaction", "body": "😂"},
             {"timestamp": start + 180, "fromMe": True, "body": "second today"}]
    said = read_group(monkeypatch, group, day="today")
    assert said.startswith("Chat with Office, today, oldest first: 2 messages, and 1 reactions left out.")
    assert "yesterday's" not in said and "😂" not in said
    assert said.index("first today") < said.index("second today")


def test_a_sticker_is_not_shown_as_a_file():
    assert whatsapp.line({"timestamp": 0, "from": "Jane Doe", "type": "sticker", "body": "", "filename": "3A5B749E.webp"}) \
        .endswith("Jane Doe: [sticker]")
