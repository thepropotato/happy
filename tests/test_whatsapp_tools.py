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

