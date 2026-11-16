"""Reading a chat says whose the last word was, and a name offered back to the person is one a lookup takes."""

import asyncio

import pytest

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


def person(name, jid=None, number="919876543210", saved=True, talked=True):
    return {"jid": jid or f"{name}@s.whatsapp.net", "name": name, "number": number, "saved": saved, "talked": talked, "group": False}


class Sends:
    def __init__(self, monkeypatch, said, earlier=(), people=None, waiting=None):
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
        monkeypatch.setattr(whatsapp, "recipients", lambda name: people if people is not None else [person(name)])
        monkeypatch.setattr(whatsapp, "waiting", dict(waiting) if waiting else {"words": None, "jids": set()})
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
    send(to="Jane Doe", message="hi", relation="brother")
    assert sends.noted == []
    sends = Sends(monkeypatch, "tell my brother jane doe hi")
    send(to="Jane Doe", message="hi", relation="brother")
    assert sends.noted


def test_a_relationship_they_said_names_the_contact_it_was_looked_up_as(monkeypatch):
    sends = Sends(monkeypatch, "tell my brother to come fast")
    send(to="John Doe", message="Come fast", relation="brother")
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


def test_stats_say_which_chats_were_busy_today(monkeypatch):
    stats = {"chats": 2, "people_chats": 1, "groups": 1, "archived": 0, "contacts": 3, "unread_messages": 0, "unread_chats": 0,
             "today": {"received": 4, "sent": 0, "chats": 2}, "this_week": {"received": 4, "sent": 0},
             "busiest_today": [{"name": "Office", "isGroup": True, "messages": 3}, {"name": "Jane Doe", "isGroup": False, "messages": 1}],
             "busiest_this_week": [], "waiting_on_your_reply": [], "biggest_groups": [], "messages_synced": 4, "synced_since": "1 Oct 2026"}
    monkeypatch.setattr(whatsapp, "bridge", lambda path, **params: stats)
    said = asyncio.run(whatsapp.whatsapp_stats())
    assert "across 2 chats: Office (group) 3, Jane Doe 1." in said


FLAT = {"to": "Jane Doe", "message": "hi", "file": "", "relation": ""}
PARAMS = {name: {} for name in FLAT}


@pytest.mark.parametrize("sent", [
    {"called": True, "called_with": FLAT},
    {"called": "whatsapp_send", "arguments": FLAT},
    {"called_by": "assistant", "name": "whatsapp_send", "arguments": FLAT},
    {"called_with": {"arguments": FLAT, "called": "whatsapp_send"}},
])
def test_buried_arguments_are_dug_out(sent):
    from happy.agent.openai_compatible import unwrapped

    assert unwrapped(sent, PARAMS) == FLAT


def test_flat_arguments_and_empty_envelopes_are_left_alone():
    from happy.agent.openai_compatible import unwrapped

    assert unwrapped(FLAT, PARAMS) == FLAT
    empty = {"called": "whatsapp_send", "called_with": {}, "error": "Missing required fields"}
    assert unwrapped(empty, PARAMS) == empty


def test_an_empty_send_does_not_demand_exact_words():
    refusal = whatsapp.wordless({"to": "Jane Doe", "message": ""})
    assert "write it in message" in refusal and "exact words" not in refusal


SCHOOL, COLLEGE = person("Jane School", number="911111111111"), person("Jane College", number="912222222222")


def test_a_name_fitting_two_contacts_asks_and_sends_nothing(monkeypatch):
    sends = Sends(monkeypatch, "tell jane hi", people=[SCHOOL, COLLEGE])
    said = send(to="jane", message="hi")
    assert "Which jane do you mean, Jane School or Jane College?" in said and sends.sent == []


def test_the_model_cannot_answer_its_own_question(monkeypatch):
    sends = Sends(monkeypatch, "tell jane hi", people=[SCHOOL, COLLEGE])
    send(to="jane", message="hi")
    monkeypatch.setattr(whatsapp, "recipients", lambda name: [SCHOOL])
    assert send(to="Jane School", message="hi").startswith("Not sent") and sends.sent == []


def test_their_choice_goes_to_the_one_chosen(monkeypatch):
    waited = {"words": "tell jane hi", "jids": {SCHOOL["jid"], COLLEGE["jid"]}}
    sends = Sends(monkeypatch, "the college one", earlier=[("tell jane hi", "Which jane?")], people=[COLLEGE], waiting=waited)
    send(to="Jane College", message="hi")
    assert sends.sent == [("send_message", {"recipients": [COLLEGE["jid"]], "message": "hi"})]


def test_two_people_with_the_very_same_name_are_told_apart_by_number(monkeypatch):
    one, two = person("John", "1@s.whatsapp.net", "911111111111"), person("John", "2@s.whatsapp.net", "912222222222")
    sends = Sends(monkeypatch, "tell john hi", people=[one, two])
    said = send(to="john", message="hi")
    assert "John ending 1 1 1 1 or John ending 2 2 2 2" in said and sends.sent == []


def test_an_exact_name_settles_it_once_they_have_been_asked(monkeypatch):
    exact, longer = person("Jane"), SCHOOL
    waited = {"words": "tell jane hi", "jids": {exact["jid"], longer["jid"]}}
    sends = Sends(monkeypatch, "just jane", earlier=[("tell jane hi", "Which jane?")], people=[exact, longer], waiting=waited)
    send(to="Jane", message="hi")
    assert sends.sent[0][1]["recipients"] == [exact["jid"]]


STRANGER = person("Jane", number="919876543210", saved=False, talked=False)


def test_a_stranger_never_written_to_needs_a_yes(monkeypatch):
    sends = Sends(monkeypatch, "tell jane hi", people=[STRANGER])
    said = send(to="Jane", message="hi")
    assert "isn't saved" in said and "3 2 1 0" in said and sends.sent == []


def test_their_yes_on_the_next_turn_sends_it(monkeypatch):
    waited = {"words": "tell jane hi", "jids": {STRANGER["jid"]}}
    sends = Sends(monkeypatch, "yes", earlier=[("tell jane hi", "Should I send it?")], people=[STRANGER], waiting=waited)
    send(to="Jane", message="hi")
    assert len(sends.sent) == 1


def test_a_yes_does_not_carry_past_the_very_next_turn(monkeypatch):
    waited = {"words": "tell jane hi", "jids": {STRANGER["jid"]}}
    sends = Sends(monkeypatch, "tell jane bye", earlier=[("what time is it", "Nine."), ("tell jane hi", "Should I send it?")], people=[STRANGER], waiting=waited)
    assert "isn't saved" in send(to="Jane", message="bye") and sends.sent == []


def test_someone_already_written_to_needs_no_yes(monkeypatch):
    sends = Sends(monkeypatch, "tell jane hi", people=[person("Jane", saved=False, talked=True)])
    send(to="Jane", message="hi")
    assert len(sends.sent) == 1


def test_a_saved_contact_never_written_to_needs_no_yes(monkeypatch):
    sends = Sends(monkeypatch, "tell jane hi", people=[person("Jane", saved=True, talked=False)])
    send(to="Jane", message="hi")
    assert len(sends.sent) == 1


def test_a_spelled_answer_settles_names_that_sound_alike(monkeypatch):
    first, second = person("Jon", "1@s.whatsapp.net"), person("John K", "2@s.whatsapp.net")
    waited = {"words": "tell jon hi", "jids": {first["jid"], second["jid"]}}
    sends = Sends(monkeypatch, "john", earlier=[("tell jon hi", "Which jon?")], people=[first, second], waiting=waited)
    send(to="John", message="hi")
    assert sends.sent[0][1]["recipients"] == [second["jid"]]
